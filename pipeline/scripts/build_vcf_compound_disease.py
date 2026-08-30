"""
VCF Compound Layer — Step 9b: disease side-table. Build now, don't surface.

Run from the repo root:  python pipeline/scripts/build_vcf_compound_disease.py

Reads:  pipeline/artifacts/vcf/compounds.jsonl            (Step 3b: compound_id, cas, pubchem_cid)
        pipeline/vendor/foodatlas_disease/entities.parquet
        pipeline/vendor/foodatlas_disease/relationships.parquet
        pipeline/vendor/foodatlas_disease/triplets.parquet
        pipeline/vendor/foodatlas_disease/evidence.parquet
        pipeline/vendor/foodatlas_disease/trust_signals.parquet
        pipeline/vendor/foodatlas_disease/attestations.parquet
        pipeline/vendor/foodatlas_disease/attestations_ambiguous.parquet
Writes: pipeline/artifacts/vcf/compound_disease.jsonl
        pipeline/artifacts/vcf/meta.json  (adds a "compound_disease" block)

FoodAtlas v4.9 bundle: released 2026-08-21, source KGC run 20260821T135611Z,
Apache-2.0. Landed as a device folder ("foodatlas-v4.9") after Step 9b was
initially blocked on a missing data source — see meta.json's provenance
note for exactly when/how.

--- Join: FoodAtlas has no CAS field on chemical entities ---

Per spec, compound_id in this table should be "CAS, from Step 3b" — but
FoodAtlas's chemical entities carry chebi/pubchem_compound/mesh/cdno
external ids, NOT CAS. The join key that actually exists on both sides is
PubChem CID: compounds.jsonl already carries `pubchem_cid` from Step 3b's
canonicalization, and 175,514 of FoodAtlas's 193,236 chemical entities
carry exactly one `pubchem_compound` id in `external_ids`. This is the
exact same join Step 6b (compound_descriptors) already uses against
FoodAtlas's metadata_flavor.tsv — reused here, not reinvented. The output
still keys each row by OUR compound_id (CAS-based per Step 3b), just
joined via CID.

96 of the ~2,356 VCF-matched PubChem CIDs resolve to more than one
FoodAtlas chemical entity (FoodAtlas has its own duplicate/legacy-record
noise, same shape as the PubChem duplicate-CID bug this build's own Step
3b spent real effort tracking down — see canonicalize_vcf_compounds.py).
Given this table is explicitly "build now, don't surface" — nothing reads
it yet, so a wrong edge here doesn't silently corrupt a live score the way
a wrong compound_id did in Step 3b — the policy is coarser than Step 3b's:
take the UNION of disease edges from every matching entity rather than
adjudicating each one by hand. Scope is recorded in meta.json so this can
be tightened later if/when the table is ever surfaced.

--- Direction: r3/r4 triplets are exclusively chemical -> disease ---

Verified directly (not assumed): every one of the 84,099 r3
(positively_correlates_with) and 46,757 r4 (negatively_correlates_with)
triplets in this release has a chemical head and a disease tail — no
food-disease or disease-disease rows leak into these two relationship
ids, so no additional entity-type filtering is needed beyond selecting
r3/r4 and restricting head to VCF-matched chemical entities.

5,618 chemical-disease pairs carry BOTH a positive and a negative
correlation triplet (conflicting literature, not a bug) — both directions
are kept as separate rows, per this table's own schema (`direction` is a
per-row field, not a per-pair verdict).

--- Evidence: PubMed-referenced, filed under FoodAtlas's "ctd" source ---

Every attestation backing an r3/r4 triplet in this release comes from
`ctd` (Comparative Toxicogenomics Database), and every one of those CTD
evidence records carries a real PMID (verified: 93,697 of 93,697). This
release's rows literally tagged source_type="pubmed" back a different
edge type (r1/CONTAINS, food-contains-chemical) and are not used here.
So "PubMed evidence" for disease correlations in this release means CTD's
own PMID citations, not FoodAtlas's separate "pubmed" source_type — worth
knowing so a future reader doesn't go looking for pubmed-tagged evidence
rows here and conclude the join is broken.

--- attestations_ambiguous: recorded per row, not used to drop edges ---

Every attestation_id in attestations_ambiguous.parquet (180,499 of
180,499) also exists in attestations.parquet — FoodAtlas's own pipeline
already resolved each ambiguous candidate set down to the single head/tail
id used to build triplets.parquet; the "ambiguous" table is an audit trail
of which resolutions had more than one candidate, not a separate set of
unresolved facts. Since triplets.parquet already reflects FoodAtlas's own
resolution, this script doesn't re-litigate it — instead, each output row
carries `n_ambiguous_attestations` (of its backing attestations) so a
future consumer can filter on ambiguity if the table is ever surfaced,
rather than that signal being silently discarded here.

--- trust_score: structurally null for every row in this release ---

trust_signals.parquet's 5,377 rows cover ONLY attestations sourced from
FoodAtlas's two LLM-literature-mining pipelines (lit2kg:claude-opus-4-8,
lit2kg:gemma-4-31B-it) — the ones extracting food-contains-chemical claims
from paper text, where an "is this plausible" pass earns its keep. Every
r3/r4 (disease correlation) attestation in this release comes from `ctd`
instead — curated, structured data, never LLM-extracted — and the overlap
between the two sets is exactly zero (verified directly). So `trust_score`
is null on every single row this script writes for THIS release, not
merely sparse. The field and the averaging logic are still implemented as
the spec asks (a future FoodAtlas release could score CTD attestations
too, or add another disease-correlation source that does), but this is
reported explicitly in meta.json rather than left to look like a bug.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
FOODATLAS_DIR = REPO_ROOT / "pipeline" / "vendor" / "foodatlas_disease"
COMPOUND_DISEASE_JSONL = OUT_DIR / "compound_disease.jsonl"
META_JSON = OUT_DIR / "meta.json"

DIRECTION_BY_REL = {
    "r3": "positive",  # positively_correlates_with
    "r4": "negative",  # negatively_correlates_with
}


def _extract_pubchem_cids(external_ids_json: str) -> list[int]:
    try:
        d = json.loads(external_ids_json)
    except (TypeError, ValueError):
        return []
    return [int(c) for c in d.get("pubchem_compound", [])]


def _extract_disease_external_id(external_ids_json: str) -> str | None:
    try:
        d = json.loads(external_ids_json)
    except (TypeError, ValueError):
        return None
    ctd_ids = d.get("ctd") or []
    return ctd_ids[0] if ctd_ids else None


def main():
    for p in (COMPOUNDS_JSONL,):
        if not p.exists():
            raise SystemExit(f"{p} not found — run canonicalize_vcf_compounds.py first.")
    required_parquet = [
        "entities.parquet", "relationships.parquet", "triplets.parquet",
        "evidence.parquet", "trust_signals.parquet",
        "attestations.parquet", "attestations_ambiguous.parquet",
    ]
    missing = [f for f in required_parquet if not (FOODATLAS_DIR / f).exists()]
    if missing:
        raise SystemExit(
            f"Missing FoodAtlas files in {FOODATLAS_DIR}: {missing} — "
            f"land the FoodAtlas v4.9 parquet bundle there first."
        )

    compounds = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]
    # A pubchem_cid can be shared by more than one compound_id in our own
    # corpus (e.g. stereoisomers Step 3b treats as one compound but which
    # kept distinct raw_compound rows) — map CID to the *set* of our
    # compound_ids so none are silently dropped.
    our_compound_ids_by_cid: dict[int, set[str]] = {}
    for c in compounds:
        if c["pubchem_cid"] is not None:
            our_compound_ids_by_cid.setdefault(c["pubchem_cid"], set()).add(c["compound_id"])

    entities = pd.read_parquet(FOODATLAS_DIR / "entities.parquet")
    chemicals = entities[entities.entity_type == "chemical"].copy()
    chemicals["cids"] = chemicals.external_ids.map(_extract_pubchem_cids)
    chem_exploded = chemicals[["foodatlas_id", "cids"]].explode("cids").dropna(subset=["cids"])
    chem_exploded["cids"] = chem_exploded["cids"].astype(int)

    vcf_cids = set(our_compound_ids_by_cid.keys())
    matched_chem = chem_exploded[chem_exploded.cids.isin(vcf_cids)]
    # entity -> set of OUR compound_ids reachable through it (usually one,
    # occasionally more when a CID maps to >1 of our compound_ids or a
    # FoodAtlas entity duplicate maps to the same CID — see module docstring)
    our_compound_ids_by_entity: dict[str, set[str]] = {}
    n_cids_multi_entity = 0
    cid_to_entities: dict[int, set[str]] = {}
    for fid, cid in zip(matched_chem.foodatlas_id, matched_chem.cids):
        our_compound_ids_by_entity.setdefault(fid, set()).update(our_compound_ids_by_cid[cid])
        cid_to_entities.setdefault(cid, set()).add(fid)
    n_cids_multi_entity = sum(1 for ids in cid_to_entities.values() if len(ids) > 1)

    diseases = entities[entities.entity_type == "disease"].copy()
    disease_common_name = dict(zip(diseases.foodatlas_id, diseases.common_name))
    disease_external_id = {
        fid: _extract_disease_external_id(ext)
        for fid, ext in zip(diseases.foodatlas_id, diseases.external_ids)
    }

    relationships = pd.read_parquet(FOODATLAS_DIR / "relationships.parquet")
    rel_name_by_id = dict(zip(relationships.foodatlas_id, relationships.name))
    assert rel_name_by_id.get("r3") == "positively_correlates_with"
    assert rel_name_by_id.get("r4") == "negatively_correlates_with"

    triplets = pd.read_parquet(FOODATLAS_DIR / "triplets.parquet")
    r34 = triplets[triplets.relationship_id.isin(["r3", "r4"])].copy()
    # Verified in exploration, asserted here so a future FoodAtlas release
    # that breaks this assumption fails loudly rather than silently
    # producing food-disease or disease-disease rows under a chemical-only
    # schema.
    entity_type_by_id = dict(zip(entities.foodatlas_id, entities.entity_type))
    bad_direction_rows = r34[
        (r34.head_id.map(entity_type_by_id) != "chemical")
        | (r34.tail_id.map(entity_type_by_id) != "disease")
    ]
    if len(bad_direction_rows):
        raise SystemExit(
            f"{len(bad_direction_rows)} r3/r4 triplet(s) are not chemical->disease "
            f"in this FoodAtlas release — the head/tail entity-type assumption "
            f"this script relies on no longer holds; re-check before proceeding."
        )

    yield_rows = r34[r34.head_id.isin(our_compound_ids_by_entity.keys())].copy()

    # --- evidence + trust_score, via each triplet's attestation_ids ---
    attestations = pd.concat(
        [pd.read_parquet(FOODATLAS_DIR / "attestations.parquet"),
         pd.read_parquet(FOODATLAS_DIR / "attestations_ambiguous.parquet")]
    )
    # attestation_id is unique within attestations.parquet and within
    # attestations_ambiguous.parquet separately, but every ambiguous-table
    # id also exists in the main table (see module docstring) — keep the
    # main table's row (first) as the canonical one for evidence_id lookup.
    attestations = attestations.drop_duplicates(subset="attestation_id", keep="first")
    ambiguous_attestation_ids = set(
        pd.read_parquet(FOODATLAS_DIR / "attestations_ambiguous.parquet").attestation_id
    )
    evidence_id_by_attestation = dict(zip(attestations.attestation_id, attestations.evidence_id))

    evidence = pd.read_parquet(FOODATLAS_DIR / "evidence.parquet")
    evidence_by_id = evidence.set_index("evidence_id")

    def pmid_for_evidence(evidence_id: str) -> str | None:
        try:
            row = evidence_by_id.loc[evidence_id]
        except KeyError:
            return None
        try:
            ref = json.loads(row["reference"])
        except (TypeError, ValueError):
            return None
        return ref.get("pmid")

    trust_signals = pd.read_parquet(FOODATLAS_DIR / "trust_signals.parquet")
    scores_by_attestation: dict[str, list[float]] = {}
    for att_id, score in zip(trust_signals.attestation_id, trust_signals.score):
        if pd.notna(score):
            scores_by_attestation.setdefault(att_id, []).append(float(score))

    out_rows = []
    n_conflicting_direction_pairs = 0
    seen_pairs_by_direction: dict[tuple, set[str]] = {"positive": set(), "negative": set()}

    for row in yield_rows.itertuples(index=False):
        direction = DIRECTION_BY_REL[row.relationship_id]
        our_ids = sorted(our_compound_ids_by_entity[row.head_id])
        att_ids = json.loads(row.attestation_ids) if isinstance(row.attestation_ids, str) else list(row.attestation_ids)

        pmids = sorted({
            pmid for pmid in (pmid_for_evidence(evidence_id_by_attestation.get(a)) for a in att_ids)
            if pmid
        })
        all_scores = [s for a in att_ids for s in scores_by_attestation.get(a, [])]
        trust_score = round(sum(all_scores) / len(all_scores), 4) if all_scores else None
        n_ambiguous = sum(1 for a in att_ids if a in ambiguous_attestation_ids)

        for our_compound_id in our_ids:
            out_rows.append(
                {
                    "compound_id": our_compound_id,
                    "disease_id": row.tail_id,
                    "disease_name": disease_common_name.get(row.tail_id),
                    "disease_external_id": disease_external_id.get(row.tail_id),
                    "direction": direction,
                    "evidence_ids": pmids,
                    "evidence_source": "ctd",
                    "n_attestations": len(att_ids),
                    "n_ambiguous_attestations": n_ambiguous,
                    "trust_score": trust_score,
                }
            )
            pair_key = (our_compound_id, row.tail_id)
            seen_pairs_by_direction[direction].add(pair_key)

    n_conflicting_direction_pairs = len(
        seen_pairs_by_direction["positive"] & seen_pairs_by_direction["negative"]
    )

    with open(COMPOUND_DISEASE_JSONL, "w") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    distinct_compounds = len({r["compound_id"] for r in out_rows})
    distinct_diseases = len({r["disease_id"] for r in out_rows})
    n_with_evidence = sum(1 for r in out_rows if r["evidence_ids"])
    n_with_trust_score = sum(1 for r in out_rows if r["trust_score"] is not None)

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["compound_disease"] = {
        "source": "FoodAtlas v4.9 (Apache-2.0), source KGC run 20260821T135611Z, released 2026-08-21",
        "provenance_note": (
            "Blocked earlier in this build — the parquet bundle wasn't present "
            "in this environment and there was no Drive file id for it in the "
            "spec's Inputs section (unlike the VCF CSVs and crosswalk). James "
            "supplied it directly as a connected device folder "
            "('foodatlas-v4.9') after being asked."
        ),
        "join_method": (
            "PubChem CID (compounds.jsonl's pubchem_cid, from Step 3b) against "
            "FoodAtlas chemical entities' external_ids.pubchem_compound — "
            "FoodAtlas has no CAS field on chemical entities, so CID is the "
            "only join key that exists on both sides. Output rows are still "
            "keyed by our own CAS-based compound_id."
        ),
        "n_foodatlas_disease_entities": int((entities.entity_type == "disease").sum()),
        "n_foodatlas_positive_correlation_triplets": int((r34.relationship_id == "r3").sum()),
        "n_foodatlas_negative_correlation_triplets": int((r34.relationship_id == "r4").sum()),
        "n_vcf_distinct_pubchem_cids": len(vcf_cids),
        "n_vcf_cids_matched_in_foodatlas": len(cid_to_entities),
        "n_cids_matching_multiple_foodatlas_entities": n_cids_multi_entity,
        "multi_entity_cid_note": (
            f"{n_cids_multi_entity} PubChem CID(s) matched more than one "
            f"FoodAtlas chemical entity (FoodAtlas's own duplicate/legacy-"
            f"record noise). Policy: union their disease edges rather than "
            f"adjudicate by hand — acceptable because this table isn't read "
            f"by any lens yet (spec: 'build now, don't surface'); revisit if "
            f"that changes."
        ),
        "n_rows_written": len(out_rows),
        "n_distinct_compounds_with_disease_edges": distinct_compounds,
        "n_distinct_diseases_touched": distinct_diseases,
        "n_rows_with_evidence_pmid": n_with_evidence,
        "n_rows_with_trust_score": n_with_trust_score,
        "trust_score_sparsity_note": (
            f"trust_score is null on every row in this release, by "
            f"construction, not as missing data: trust_signals.parquet's "
            f"{len(trust_signals)} rows cover only LLM-literature-mining-"
            f"sourced attestations (lit2kg:*), which back a different edge "
            f"type (CONTAINS). Every r3/r4 disease-correlation attestation "
            f"in this release comes from FoodAtlas's 'ctd' source instead, "
            f"and the overlap between the two attestation sets is exactly "
            f"zero (verified). The averaging logic is implemented and will "
            f"activate automatically if a future FoodAtlas release scores "
            f"CTD attestations or adds another scored disease-correlation "
            f"source."
        ),
        "evidence_source_note": (
            "Every r3/r4-backing attestation in this release comes from "
            "FoodAtlas's 'ctd' source (Comparative Toxicogenomics Database), "
            "every one of which cites a real PMID. FoodAtlas's own "
            "source_type='pubmed' evidence rows back a different edge type "
            "(r1/CONTAINS) and are not used here."
        ),
        "n_chemical_disease_pairs_with_conflicting_direction": n_conflicting_direction_pairs,
        "conflicting_direction_note": (
            f"{n_conflicting_direction_pairs} (compound, disease) pair(s) have "
            f"BOTH a positive and a negative correlation row — conflicting "
            f"literature, not a bug. Both rows are kept; direction is a "
            f"per-row field here, not a per-pair verdict."
        ),
        "not_wired_into_any_lens": (
            "Per spec: stored, not displayed. Surfacing food-disease "
            "correlations is a regulated health claim. No frontend or API "
            "code reads this table."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {len(out_rows)} compound_disease rows to {COMPOUND_DISEASE_JSONL}")
    print(f"  {distinct_compounds} distinct compounds with >=1 disease edge")
    print(f"  {distinct_diseases} distinct diseases touched")
    print(f"  {n_with_evidence} rows have >=1 PMID, {n_with_trust_score} rows have a trust_score")
    print(f"  {n_conflicting_direction_pairs} (compound, disease) pairs have conflicting direction")
    print(f"  {n_cids_multi_entity} CIDs matched >1 FoodAtlas chemical entity (union policy)")


if __name__ == "__main__":
    main()
