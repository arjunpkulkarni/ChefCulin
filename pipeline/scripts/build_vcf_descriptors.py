"""
VCF Compound Layer — Step 6b: odor/flavor descriptor table.

Run from the repo root:  python pipeline/scripts/build_vcf_descriptors.py

Reads:  pipeline/artifacts/vcf/compounds.jsonl
        pipeline/vendor/foodatlas/metadata_flavor.tsv
Writes: pipeline/artifacts/vcf/compound_descriptors.jsonl
        pipeline/artifacts/vcf/meta.json   (adds a "descriptors" block)

Per spec, this is a cached, offline table — never queried live — sourced
from FoodAtlas + Flavornet. Flavornet is NOT included in this build:
flavornet.org was unreachable from this environment (robots.txt fetch
timed out on the live site; the Wayback Machine mirror was blocked by the
fetch proxy). Reported to James 2026-08-28 rather than silently shipping a
single-source table under a "two sources" label. FoodAtlas alone is what's
built here; Flavornet can be added later as a second source without
reshaping this table — merge_priority already treats source as an ordered
field for exactly that reason.

FoodAtlas's metadata_flavor.tsv itself blends two of ITS OWN upstream
sources (both apparently already deduped/normalized into FoodAtlas's own
metadata layer, not something added here):
  flavordb (4,511 rows) — purpose-built flavor/aroma descriptors
    (sweet, fruity, green, woody, ...). Preferred.
  hsdb     (1,189 rows) — Hazardous Substances Data Bank odor notes.
    Useful when specific ("garlic", "almond") but a meaningful share are
    generic safety-sheet phrasing ("characteristic odor", "odorless") that
    carries little explanatory value. Lower priority than flavordb.
Compound identity: metadata_flavor.tsv keys to PubChem CID
(`_chemical_name` = "PUBCHEM_COMPOUND:<cid>"), which is exactly the join
key compounds.jsonl already carries from Step 3b's canonicalization — no
name matching needed, no ambiguity.

Coverage check (spec-mandated, not a pass/fail gate — the spec's own point
is that this number is expected to be low): of the 30 highest-IDF compounds
that actually show up as "explanatory" in pairs.jsonl's top_shared_compounds
lists, what fraction have any descriptor at all. Recorded in meta.json, not
asserted against a threshold.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
PAIRS_JSONL = OUT_DIR / "pairs.jsonl"
FOODATLAS_FLAVOR_TSV = REPO_ROOT / "pipeline" / "vendor" / "foodatlas" / "metadata_flavor.tsv"
DESCRIPTORS_JSONL = OUT_DIR / "compound_descriptors.jsonl"
META_JSON = OUT_DIR / "meta.json"

# Lower number = preferred when a compound has descriptors from more than
# one source. flavordb is purpose-built for flavor; hsdb trends toward
# safety-sheet phrasing (see module docstring).
SOURCE_PRIORITY = {"flavordb": 1, "hsdb": 2}

CID_RE = re.compile(r"^PUBCHEM_COMPOUND:(\d+)$")

# Descriptor strings that carry ~no explanatory content for a chef-facing
# pairing lens — kept in the raw table (nothing is discarded) but excluded
# from the coverage check so the "does this compound have a USEFUL
# descriptor" number isn't inflated by "odorless"/"characteristic odor".
LOW_INFO_DESCRIPTORS = {"odorless", "tasteless", "characteristic odor", "faint", "odor"}

# FoodAtlas's own metadata_flavor.tsv mixes detection-threshold /
# concentration data into the _flavor_name field for ~0.7% of rows (both
# flavordb- and hsdb-sourced) — e.g. "1.10x10-4 m/l (recognition in water,
# chemically pure)", "taste threshold: 1.60x10-4 moles/l ...". That's not a
# descriptor, it's a concentration figure, and it would actively mislead if
# it ever surfaced as an "odor descriptor" for a compound. Dropped entirely
# at ingestion rather than kept-but-flagged: a handful mix a real
# descriptor phrase in with the number ("taste characteristics at 20 ppm:
# floral, rose, sweet..."), but reliably splitting that out is fragile for
# 40 rows out of 5,700 — not worth the risk of a bad regex silently
# corrupting a real descriptor elsewhere.
THRESHOLD_VALUE_RE = re.compile(
    r"\b(ppm|ppb|mg/cu|mg/l|mg/m|m/l|moles?/l|threshold)\b|\d+\.\d+x10", re.IGNORECASE
)


def main():
    if not COMPOUNDS_JSONL.exists():
        raise SystemExit(f"{COMPOUNDS_JSONL} not found — run the earlier steps first.")
    if not FOODATLAS_FLAVOR_TSV.exists():
        raise SystemExit(f"{FOODATLAS_FLAVOR_TSV} not found — see module docstring for where it comes from.")

    compound_rows = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]
    # One representative row per compound_id (idf/df/group are identical
    # across raw-string duplicates; pubchem_cid is what we join on).
    by_compound_id = {}
    for r in compound_rows:
        by_compound_id.setdefault(r["compound_id"], r)
    cid_to_compound_id: dict[int, list[str]] = defaultdict(list)
    for cid_str, r in by_compound_id.items():
        pcid = r.get("pubchem_cid")
        if pcid is not None:
            cid_to_compound_id[int(pcid)].append(cid_str)

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    raw_rows = []
    unmatched_cids = 0
    n_threshold_dropped = 0
    with open(FOODATLAS_FLAVOR_TSV) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            m = CID_RE.match(row["_chemical_name"])
            if not m:
                continue  # none observed in this file, but don't assume forever
            if THRESHOLD_VALUE_RE.search(row["_flavor_name"]):
                n_threshold_dropped += 1
                continue
            pcid = int(m.group(1))
            compound_ids = cid_to_compound_id.get(pcid)
            if not compound_ids:
                unmatched_cids += 1
                continue
            for cid_str in compound_ids:
                raw_rows.append(
                    {
                        "compound_id": cid_str,
                        "cas": by_compound_id[cid_str].get("cas"),
                        "pubchem_cid": pcid,
                        "descriptor": row["_flavor_name"].strip().rstrip("."),
                        "source": row["source"],
                        "priority": SOURCE_PRIORITY.get(row["source"], 99),
                        "fetched_at": fetched_at,
                    }
                )

    # Dedup identical (compound_id, descriptor, source) triples — FoodAtlas
    # itself has a few exact repeats.
    seen = set()
    descriptor_rows = []
    for r in raw_rows:
        key = (r["compound_id"], r["descriptor"], r["source"])
        if key in seen:
            continue
        seen.add(key)
        descriptor_rows.append(r)

    descriptor_rows.sort(key=lambda r: (r["compound_id"], r["priority"], r["descriptor"]))

    with open(DESCRIPTORS_JSONL, "w") as f:
        for r in descriptor_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_compounds_with_descriptor = len({r["compound_id"] for r in descriptor_rows})
    n_compounds_total = len(by_compound_id)
    source_counts = Counter(r["source"] for r in descriptor_rows)

    # --- coverage check against the actually-explanatory compounds ---
    coverage = None
    if PAIRS_JSONL.exists():
        pair_rows = [json.loads(l) for l in PAIRS_JSONL.read_text().splitlines() if l.strip()]
        idf_by_compound: dict[str, float] = {}
        for pr in pair_rows:
            for c in pr["top_shared_compounds"]:
                idf_by_compound[c["compound_id"]] = c["idf"]
        top30 = sorted(idf_by_compound.items(), key=lambda kv: kv[1], reverse=True)[:30]
        top30_ids = [cid for cid, _ in top30]
        descriptor_by_id: dict[str, list[str]] = defaultdict(list)
        for r in descriptor_rows:
            descriptor_by_id[r["compound_id"]].append(r["descriptor"])
        n_any = sum(1 for cid in top30_ids if descriptor_by_id.get(cid))
        n_useful = sum(
            1 for cid in top30_ids
            if any(d not in LOW_INFO_DESCRIPTORS for d in descriptor_by_id.get(cid, []))
        )
        coverage = {
            "n_checked": len(top30_ids),
            "n_with_any_descriptor": n_any,
            "n_with_useful_descriptor": n_useful,
            "examples_covered": [
                {"compound_id": cid, "descriptors": descriptor_by_id[cid]}
                for cid in top30_ids if descriptor_by_id.get(cid)
            ][:10],
            "examples_uncovered": [cid for cid in top30_ids if not descriptor_by_id.get(cid)][:10],
        }

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["descriptors"] = {
        "sources_used": ["foodatlas:flavordb", "foodatlas:hsdb"],
        "sources_attempted_not_available": [
            {
                "source": "flavornet",
                "reason": (
                    "flavornet.org unreachable from this environment (robots.txt fetch "
                    "timed out on the live site; web.archive.org mirror blocked by the "
                    "fetch proxy, HTTP 403). Reported to James 2026-08-28. Can be added "
                    "later without reshaping this table — source/priority are already "
                    "per-row fields."
                ),
            }
        ],
        "n_raw_descriptor_rows_foodatlas": len(descriptor_rows),
        "n_threshold_value_rows_dropped": n_threshold_dropped,
        "source_counts": dict(source_counts),
        "n_distinct_compounds_in_source": len(cid_to_compound_id),
        "n_pubchem_cids_unmatched_to_corpus": unmatched_cids,
        "n_compounds_with_any_descriptor": n_compounds_with_descriptor,
        "n_compounds_total": n_compounds_total,
        "coverage_fraction": round(n_compounds_with_descriptor / n_compounds_total, 4),
        "coverage_check_top30_explanatory_compounds": coverage,
        "fetched_at": fetched_at,
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {len(descriptor_rows)} descriptor rows ({n_compounds_with_descriptor} distinct compounds) to {DESCRIPTORS_JSONL}")
    print(f"Source counts: {dict(source_counts)}")
    print(f"Overall coverage: {n_compounds_with_descriptor}/{n_compounds_total} = {n_compounds_with_descriptor/n_compounds_total:.1%}")
    if coverage:
        print(f"Top-30 explanatory-compound coverage: {coverage['n_with_any_descriptor']}/{coverage['n_checked']} any descriptor, "
              f"{coverage['n_with_useful_descriptor']}/{coverage['n_checked']} useful (non-generic) descriptor")


if __name__ == "__main__":
    main()
