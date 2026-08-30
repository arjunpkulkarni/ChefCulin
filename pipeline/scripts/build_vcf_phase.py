"""
VCF Compound Layer — Step 11a/11b: phase behaviour, part 1 (XLogP + buckets).

Run from the repo root, AFTER canonicalize_vcf_compounds.py (needs `cas`)
and build_vcf_profiles.py (needs `compound_group`/`idf` already present,
though this script doesn't itself require idf — run order matches the
established full-rebuild chain so compounds.jsonl carries everything by
the time this runs):
    python pipeline/scripts/build_vcf_phase.py

Reads:  pipeline/artifacts/vcf/compounds.jsonl
        pipeline/vendor/vcf/vcfodor_cas_pubchem_distinct.xlsx
Writes: pipeline/artifacts/vcf/compounds.jsonl   (same file, in place —
        adds `xlogp`, `molecular_weight`, `tpsa`, `phase_bucket`)
        pipeline/artifacts/vcf/meta.json         (adds a "phase" block)

Per spec 11a: the crosswalk used for CAS/PubChem identity in Step 3b
already carries XLogP (octanol-water partition coefficient — the direct
measure of fat vs water affinity), MolecularWeight, and TPSA on the large
majority of its 5,879 rows. No new fetch is needed for this half of Step
11; join on `cas`, the same key Step 3b already attached.

One thing the spec doesn't mention, found while building this: the
crosswalk's XLogP column is not numeric-clean — 143 of 5,879 rows carry
the literal string "$null$" instead of a number (pandas reads the column
as dtype=object because of this). Treated as missing, not coerced to 0.0
and not dropped from the row — this is exactly the case Step 11's own
reliability anchor calls out: "no silent zeros." A compound with a CAS in
the crosswalk but a "$null$" XLogP gets `xlogp: null`, `phase_bucket:
null`, same as a compound with no CAS at all — both are honestly "we don't
know", not "assumed zero" (which would misclassify it into water_phase).

--- 11b: phase buckets ---

Cut points per spec, applied as half-open intervals so every value lands
in exactly one bucket with no ambiguity at the boundaries:
  water_phase  : xlogp <  0
  both_phases  : 0  <= xlogp <  2
  fat_leaning  : 2  <= xlogp <  4
  fat_phase    : xlogp >= 4
Compounds with no xlogp (unmatched name, or a "$null$" crosswalk row) get
phase_bucket = null — they are not assigned to water_phase by default,
which would be a silent, wrong assumption in the other direction.

Per-Compound-Group median xlogp is also computed and stored, both per
compound (so callers can compare an individual compound's own xlogp
against its group's typical value) and as a summary table in meta.json —
this is what the spec's Step 11 reliability anchors check against
(Hydrocarbons highest of the 18 groups; Bases and Furans below
Hydrocarbons, Esters, and Phenols).
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CROSSWALK_XLSX = REPO_ROOT / "pipeline" / "vendor" / "vcf" / "vcfodor_cas_pubchem_distinct.xlsx"
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
META_JSON = OUT_DIR / "meta.json"


def to_float_or_none(v) -> float | None:
    """Crosswalk numeric columns carry a literal '$null$' string for some
    rows rather than an empty cell — pandas can't infer that as NaN on its
    own (that's why XLogP loads as dtype=object). Anything that doesn't
    parse as a float is missing, not zero."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def phase_bucket(xlogp: float | None) -> str | None:
    if xlogp is None:
        return None
    if xlogp < 0:
        return "water_phase"
    if xlogp < 2:
        return "both_phases"
    if xlogp < 4:
        return "fat_leaning"
    return "fat_phase"


def load_crosswalk_props() -> dict[str, dict]:
    xw = pd.read_excel(CROSSWALK_XLSX)
    props: dict[str, dict] = {}
    for row in xw.itertuples(index=False):
        cas = row.CAS
        # A handful of CAS values repeat under the "exact_ambiguous_name"
        # tie-break in Step 3b (lower CAS wins) — irrelevant here, this is
        # keyed by CAS directly and every CAS's own row carries its own
        # properties regardless of which Name string it was matched under.
        props[cas] = {
            "xlogp": to_float_or_none(row.XLogP),
            "molecular_weight": to_float_or_none(row.MolecularWeight),
            "tpsa": to_float_or_none(row.TPSA),
        }
    return props


def main():
    if not COMPOUNDS_JSONL.exists():
        raise SystemExit(f"{COMPOUNDS_JSONL} not found — run canonicalize_vcf_compounds.py first.")
    if not CROSSWALK_XLSX.exists():
        raise SystemExit(f"{CROSSWALK_XLSX} not found.")

    props_by_cas = load_crosswalk_props()
    rows = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]

    n_with_xlogp = 0
    group_values: dict[str, list[float]] = {}
    bucket_counts: dict[str, int] = {}

    for r in rows:
        cas = r.get("cas")
        props = props_by_cas.get(cas) if cas else None
        xlogp = props["xlogp"] if props else None
        r["xlogp"] = xlogp
        r["molecular_weight"] = props["molecular_weight"] if props else None
        r["tpsa"] = props["tpsa"] if props else None
        bucket = phase_bucket(xlogp)
        r["phase_bucket"] = bucket

        if xlogp is not None:
            n_with_xlogp += 1
            group = r.get("compound_group")
            # Beef Ingestion Build Spec Step 3: a genuinely new compound
            # whose beef-sheet group label didn't map cleanly to one of
            # VCF's 18 groups is stored with compound_group=None (reported
            # in meta.json's protein_beef block), never guessed. It still
            # has a phase_bucket (xlogp doesn't depend on group), but it
            # can't contribute to any GROUP's median — there's no group.
            if group is not None:
                group_values.setdefault(group, []).append(xlogp)
        if bucket is not None:
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    with open(COMPOUNDS_JSONL, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_total = len(rows)
    n_bucketed = sum(bucket_counts.values())
    all_xlogp = sorted(v for r in rows if r["xlogp"] is not None for v in [r["xlogp"]])

    def quantile(sorted_vals, q):
        if not sorted_vals:
            return None
        idx = (len(sorted_vals) - 1) * q
        lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
        frac = idx - lo
        return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac

    group_medians = {
        g: {"n": len(vals), "median_xlogp": round(statistics.median(vals), 2)}
        for g, vals in group_values.items()
    }
    group_medians_sorted = dict(
        sorted(group_medians.items(), key=lambda kv: -kv[1]["median_xlogp"])
    )

    top_group = next(iter(group_medians_sorted)) if group_medians_sorted else None
    hydrocarbons_is_top = top_group == "Hydrocarbons"
    hydrocarbons_median = group_medians.get("Hydrocarbons", {}).get("median_xlogp")
    bases_median = group_medians.get("Bases", {}).get("median_xlogp")
    furans_median = group_medians.get("Furans", {}).get("median_xlogp")
    esters_median = group_medians.get("Esters", {}).get("median_xlogp")
    phenols_median = group_medians.get("Phenols", {}).get("median_xlogp")
    bases_furans_below_others = all(
        v is not None and hydrocarbons_median is not None and v < hydrocarbons_median
        and esters_median is not None and v < esters_median
        and phenols_median is not None and v < phenols_median
        for v in (bases_median, furans_median)
        if v is not None
    )

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["phase"] = {
        "n_compounds_total": n_total,
        "n_compounds_with_xlogp": n_with_xlogp,
        "xlogp_coverage": round(n_with_xlogp / n_total, 4),
        "n_crosswalk_rows_null_xlogp_string": sum(
            1 for v in props_by_cas.values() if v["xlogp"] is None
        ),
        "overall_median_xlogp": round(statistics.median(all_xlogp), 2) if all_xlogp else None,
        "overall_quartiles_xlogp": [
            round(quantile(all_xlogp, 0.25), 2) if all_xlogp else None,
            round(quantile(all_xlogp, 0.75), 2) if all_xlogp else None,
        ],
        "bucket_counts": bucket_counts,
        "bucket_shares": {
            k: round(v / n_bucketed, 4) for k, v in bucket_counts.items()
        } if n_bucketed else {},
        "group_medians_xlogp": group_medians_sorted,
        "reliability_hydrocarbons_top_group": hydrocarbons_is_top,
        "reliability_bases_furans_below_hydrocarbons_esters_phenols": bases_furans_below_others,
        "bucket_cutpoints_note": (
            "water_phase: xlogp<0; both_phases: 0<=xlogp<2; fat_leaning: "
            "2<=xlogp<4; fat_phase: xlogp>=4. Half-open intervals so every "
            "value lands in exactly one bucket. Compounds with no xlogp "
            "(no CAS match, or a crosswalk '$null$' row) get "
            "phase_bucket=null, not defaulted into water_phase."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"XLogP joined for {n_with_xlogp}/{n_total} compounds ({n_with_xlogp/n_total:.1%})")
    print(f"Crosswalk rows with literal '$null$' XLogP: "
          f"{meta['phase']['n_crosswalk_rows_null_xlogp_string']}")
    print(f"Overall median xlogp: {meta['phase']['overall_median_xlogp']}  "
          f"quartiles: {meta['phase']['overall_quartiles_xlogp']}")
    print("Bucket shares:")
    for k, v in meta["phase"]["bucket_shares"].items():
        print(f"  {k:<14} {bucket_counts[k]:>5}  ({v:.1%})")
    print("\nGroup medians (xlogp, descending):")
    for g, info in group_medians_sorted.items():
        print(f"  {g:<20} n={info['n']:<5} median={info['median_xlogp']}")
    print(f"\nHydrocarbons is top group: {hydrocarbons_is_top}")
    print(f"Bases/Furans below Hydrocarbons/Esters/Phenols: {bases_furans_below_others}")


if __name__ == "__main__":
    main()
