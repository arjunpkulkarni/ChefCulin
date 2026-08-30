"""
VCF Compound Layer — Step 8: form diffs (the Form lens's actual data).

Run from the repo root:  python pipeline/scripts/build_vcf_form_diffs.py

Reads:  pipeline/artifacts/vcf/spine.jsonl      (Step 3, base_ingredient -> members)
        pipeline/artifacts/vcf/profiles.jsonl   (Step 4, compound_ids per product)
        pipeline/artifacts/vcf/compounds.jsonl  (Step 3b/4, df_culinary + idf)
Writes: pipeline/artifacts/vcf/form_diffs.jsonl
        pipeline/artifacts/vcf/meta.json  (adds a "form_diffs" block)

    gained = profile[to] - profile[from]
    lost   = profile[from] - profile[to]

"Preparation state" in the spec's own examples (PEANUT raw/roasted, PORK's
cure x prep combinations) is really "distinct product-level variant of one
base_ingredient" — cure_state and form (PEANUT BUTTER, PEANUT OIL) vary the
profile exactly the same way preparation does, and the spine already
grouped every such variant of one base_ingredient into one entry's
`members` in Step 3. So the unit of comparison here is the spine member
(vcf_product_id), not a parsed preparation label — no new grouping logic,
just diffing what Step 3 already grouped.

Scope: CULINARY members only, matching every earlier step's corpus
decision (Step 3's IDF-corpus exclusion, Step 4's profile/IDF computation,
Step 5's pairing). Reference members (essential oils, isolated extracts)
aren't collected as a "form" a chef produces by cooking, and mixing them in
would compare across two different notions of "state" silently — the same
failure mode Step 4 warns about for mixing profile sources.

For every spine entry with >=2 culinary members, every unordered pair of
those members gets a diff, stored as two directed rows (A->B and B->A) so
a lens can query either product as the anchor without swapping fields at
read time — pairs.jsonl already double-stores anchor perspectives for the
same reason. Pairwise, not anchored on "raw": several bases here have no
raw member at all (PEANUT's set includes BUTTER and OIL; PORK's ten members
split cured/uncured x five preparations with no single obvious baseline),
and picking one member as "the" reference for every comparison would be
exactly the asserted-not-measured move the spec warns against. All pairs
are stored; a lens picks which comparison it wants.

Document-frequency floor of df_culinary >= 3, applied before ranking by
idf descending — per spec, unfiltered IDF on PEANUT (raw) -> PEANUT
(roasted) returns five singleton compounds on the lost side, technically
"distinctive" but culinarily meaningless; the floor is what turns that into
the real signal (cinnamic acids at df 4-9). gained_total/lost_total are
recorded unfiltered so the floor's effect stays visible rather than
disappearing into the filtered list.

Spine entries with 0 or 1 culinary members are NOT in form_diffs.jsonl at
all — that's deliberate, not an omission to paper over. Per spec: "where an
ingredient has only one state, the lens must say so rather than generate a
comparison." meta.json's "form_diffs" block carries the full breakdown (0
culinary members / exactly 1 / 2+) precisely so a caller can tell "no diff
exists because there's only one form" apart from "no diff exists because
this spine_id isn't in the corpus at all" without guessing from absence.
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
SPINE_JSONL = OUT_DIR / "spine.jsonl"
PROFILES_JSONL = OUT_DIR / "profiles.jsonl"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
FORM_DIFFS_JSONL = OUT_DIR / "form_diffs.jsonl"
META_JSON = OUT_DIR / "meta.json"

# Beef Ingestion Build Spec, Step 7: "aging deltas as a distinct diff
# type" — a QUANTITATIVE value_a/value_b delta between two pre_treatments
# (dry-aged vs wet-aged, both at day 28), not a gained/lost SET diff
# between two profiles. Produced by ingest_protein_beef.py from Beef
# Quantitative Deltas' dry28_vs_wet28 rows; appended here, after the
# ordinary state_diff rows, tagged with a diff_type field so a reader can
# tell the two shapes apart (state_diff rows get diff_type added too, for
# the same reason — additive, no existing field removed or renamed).
AGING_DELTAS_JSONL = REPO_ROOT / "pipeline" / "artifacts" / "protein" / "beef_aging_deltas.jsonl"

DF_FLOOR = 3

# Validation target from the spec: PEANUT (raw) -> PEANUT (roasted), lost
# side, floored at df>=3, should surface cinnamic-acid-family compounds
# (df 4-9) rather than the unfiltered singleton noise.
VALIDATION_FROM = "PEANUT (raw)"
VALIDATION_TO = "PEANUT (roasted)"


def diff_side(from_ids: set, to_ids: set, compound_meta: dict) -> tuple[list[dict], int]:
    """Compounds in from_ids but not to_ids ('lost' when from_ids is the
    anchor), floored at DF_FLOOR and ranked by idf descending. Returns
    (filtered_ranked_list, unfiltered_count)."""
    raw_diff = from_ids - to_ids
    floored = [c for c in raw_diff if compound_meta[c]["df_culinary"] >= DF_FLOOR]
    ranked = sorted(floored, key=lambda c: (-(compound_meta[c]["idf"] or 0.0), c))
    entries = [
        {
            "compound_id": c,
            "raw_compound": compound_meta[c]["raw_compound"],
            "compound_group": compound_meta[c]["compound_group"],
            "df_culinary": compound_meta[c]["df_culinary"],
            "idf": compound_meta[c]["idf"],
        }
        for c in ranked
    ]
    return entries, len(raw_diff)


def main():
    for p in (SPINE_JSONL, PROFILES_JSONL, COMPOUNDS_JSONL):
        if not p.exists():
            raise SystemExit(f"{p} not found — run the earlier steps first.")

    spine = [json.loads(l) for l in SPINE_JSONL.read_text().splitlines() if l.strip()]
    profiles = [json.loads(l) for l in PROFILES_JSONL.read_text().splitlines() if l.strip()]
    compound_rows = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]

    by_pid = {p["vcf_product_id"]: p for p in profiles}
    compound_meta = {r["compound_id"]: r for r in compound_rows}

    n_zero_culinary = 0
    n_single_culinary = 0
    n_multi_culinary = 0
    single_state_spine_ids: list[str] = []
    diff_rows = []
    pair_count = 0

    for entry in spine:
        culinary_members = [
            by_pid[m["vcf_product_id"]]
            for m in entry["members"]
            if by_pid[m["vcf_product_id"]]["class"] == "culinary"
        ]
        n = len(culinary_members)
        if n == 0:
            n_zero_culinary += 1
            continue
        if n == 1:
            n_single_culinary += 1
            single_state_spine_ids.append(entry["spine_id"])
            continue
        n_multi_culinary += 1

        for a, b in itertools.combinations(culinary_members, 2):
            pair_count += 1
            set_a, set_b = set(a["compound_ids"]), set(b["compound_ids"])

            # a -> b: gained = b - a, lost = a - b
            gained_ab, gained_ab_total = diff_side(set_b, set_a, compound_meta)
            lost_ab, lost_ab_total = diff_side(set_a, set_b, compound_meta)
            diff_rows.append(
                {
                    "diff_type": "state_diff",
                    "spine_id": entry["spine_id"],
                    "base_ingredient": entry.get("base_ingredient", entry["spine_id"]),
                    "from_vcf_product_id": a["vcf_product_id"],
                    "from_raw_name": a["raw_name"],
                    "to_vcf_product_id": b["vcf_product_id"],
                    "to_raw_name": b["raw_name"],
                    "df_floor": DF_FLOOR,
                    "gained_total": gained_ab_total,
                    "lost_total": lost_ab_total,
                    "gained": gained_ab,
                    "lost": lost_ab,
                }
            )
            # b -> a: mirror
            diff_rows.append(
                {
                    "diff_type": "state_diff",
                    "spine_id": entry["spine_id"],
                    "base_ingredient": entry.get("base_ingredient", entry["spine_id"]),
                    "from_vcf_product_id": b["vcf_product_id"],
                    "from_raw_name": b["raw_name"],
                    "to_vcf_product_id": a["vcf_product_id"],
                    "to_raw_name": a["raw_name"],
                    "df_floor": DF_FLOOR,
                    "gained_total": lost_ab_total,
                    "lost_total": gained_ab_total,
                    "gained": lost_ab,
                    "lost": gained_ab,
                }
            )

    # --- validation: PEANUT raw -> roasted, lost side should show cinnamic
    # acids at df 4-9, not unfiltered singletons ---
    validation = next(
        (
            r for r in diff_rows
            if r["from_raw_name"] == VALIDATION_FROM and r["to_raw_name"] == VALIDATION_TO
        ),
        None,
    )
    validation_report = None
    if validation is not None:
        validation_report = {
            "from": VALIDATION_FROM,
            "to": VALIDATION_TO,
            "lost_total_unfiltered": validation["lost_total"],
            "lost_after_df_floor": [
                {"raw_compound": e["raw_compound"], "df_culinary": e["df_culinary"]}
                for e in validation["lost"]
            ],
        }
        print(f"Validation ({VALIDATION_FROM} -> {VALIDATION_TO}), lost side after df>={DF_FLOOR} floor:")
        for e in validation["lost"]:
            print(f"  {e['raw_compound']}  df={e['df_culinary']}  idf={e['idf']:.3f}")
    else:
        print(f"NOTE: validation pair {VALIDATION_FROM!r} -> {VALIDATION_TO!r} not found in this corpus "
              f"(product names may differ in the full pull) — reported, not fatal.")

    n_aging_delta_rows = 0
    if AGING_DELTAS_JSONL.exists():
        aging_rows = [json.loads(l) for l in AGING_DELTAS_JSONL.read_text().splitlines() if l.strip()]
        diff_rows.extend(aging_rows)
        n_aging_delta_rows = len(aging_rows)

    with open(FORM_DIFFS_JSONL, "w") as f:
        for r in diff_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["form_diffs"] = {
        "n_aging_delta_rows_appended": n_aging_delta_rows,
        "aging_delta_note": (
            "A quantitative value_a/value_b delta (dry-aged vs wet-aged, day 28), not a gained/lost "
            "set diff — kept as its own diff_type so a reader never confuses the two shapes. See "
            "ingest_protein_beef.py."
        ),
        "n_spine_entries_total": len(spine),
        "n_spine_zero_culinary_members": n_zero_culinary,
        "n_spine_single_state_culinary": n_single_culinary,
        "n_spine_multi_state_culinary": n_multi_culinary,
        "form_lens_size_note": (
            f"{n_multi_culinary} base ingredients have more than one culinary "
            f"form — that is the real size of the Form lens from the full pull."
        ),
        "sample_comparison_182_products": {
            "multi_state_of_total_base_names": "24 of 132",
            "note": "4 of the sample's top 6 by member count were essential oils.",
        },
        "n_diff_pairs_unordered": pair_count,
        "n_diff_rows_written": len(diff_rows),
        "df_floor": DF_FLOOR,
        "single_state_spine_ids_sample": single_state_spine_ids[:20],
        "n_single_state_spine_ids_total": len(single_state_spine_ids),
        "validation_peanut_raw_to_roasted": validation_report,
        "note": (
            "Spine entries with 0 or 1 culinary members are deliberately absent "
            "from form_diffs.jsonl — a lens must report 'only one known form' "
            "for those rather than fabricate a comparison. This block is how a "
            "caller tells that case apart from 'not in the corpus at all' "
            "(0 culinary members) without guessing from absence."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"\nWrote {len(diff_rows)} form-diff rows ({pair_count} unordered pairs) to {FORM_DIFFS_JSONL}")
    print(f"Spine entries: {len(spine)} total — {n_multi_culinary} multi-state (diffable), "
          f"{n_single_culinary} single-state, {n_zero_culinary} zero-culinary")
    print(f"Form lens size: {n_multi_culinary} base ingredients  (sample: 24 of 132)")


if __name__ == "__main__":
    main()
