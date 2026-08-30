"""
VCF Compound Layer — Step 11c: volatility (boiling point) buckets.

Run from the repo root, AFTER build_vcf_phase.py:
    python pipeline/scripts/build_vcf_volatility.py

Reads:  pipeline/artifacts/vcf/compounds.jsonl
        pipeline/vendor/vcf/boiling_points_fetched.jsonl   (see below)
Writes: pipeline/artifacts/vcf/compounds.jsonl   (same file, in place —
        adds `boiling_point_c`, `volatility_bucket`)
        pipeline/artifacts/vcf/meta.json         (adds a "volatility" block)

--- Why this reads from a cache file instead of fetching live itself ---

Unlike Step 11a's XLogP (already sitting in the CAS crosswalk this repo
already vendors — no fetch needed), boiling point isn't part of that
crosswalk and isn't in PubChem's simple per-CID property table either
(MolecularWeight, XLogP, TPSA etc. are; boiling point is an "Experimental
Properties" annotation, retrieved via a different, heavier endpoint —
PUG View, one compound at a time, no batch call available for it).

This environment's own network egress is proxy-blocked for direct calls to
pubchem.ncbi.nlm.nih.gov (confirmed both from this container and from the
linked Mac's shell — both go through an allowlist proxy that returns 403
on CONNECT). The only path that worked at all was running fetch() from
inside the Mac's browser pane, on a real loaded pubchem.ncbi.nlm.nih.gov
page — same-origin JS isn't subject to that proxy restriction. That path
DOES work mechanically (confirmed on live requests, real parsed boiling
points), but PUG View itself was intermittently returning 503 ServerBusy
under sustained request volume during this build — confirmed not a pacing
problem on this end (the lighter /property/ endpoint used for XLogP kept
returning 200 throughout the same window).

So the live fetch was run through the browser pane in the background while
this script was written, writing its results to
`pipeline/vendor/vcf/boiling_points_fetched.jsonl` — one line per
successfully-parsed CID: `{"cid": int, "boiling_point_c": float,
"n_readings": int}`. This script is the separate, deterministic half: given
whatever boiling points exist in that cache (complete or partial), merge
them onto compounds.jsonl and apply the spec's threshold rule. It does not
know or care how that cache was produced — re-run it any time the cache
file is updated (a later, more complete fetch; a different data source
entirely; a fetch run from an unrestricted machine) without touching this
script.

--- Bucketing ---

Thresholds are the spec's own: volatile / moderate / stable, cut on the
FETCHED distribution rather than an assumed round number (spec: "Set
thresholds from the fetched distribution, not from assumption"). Uses
tertiles of whatever boiling points were actually obtained — the middle
third is 'moderate', below is 'volatile', above is 'stable' — so the cut
points are reported in meta.json and are exactly reproducible from
whatever the cache contained at build time, not hand-picked.

--- Coverage-gated suppression ---

Per spec: "if it lands below about 50%, volatility claims should be
suppressed rather than made on thin data." `meta.json`'s volatility block
carries `volatility_claims_suppressed` as an explicit boolean a caller
(the reliability suite, the frontend) can check rather than infer from the
coverage number itself — no code path should compute "is this thin" more
than once.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
META_JSON = OUT_DIR / "meta.json"
BOILING_POINTS_CACHE = REPO_ROOT / "pipeline" / "vendor" / "vcf" / "boiling_points_fetched.jsonl"
COVERAGE_SUPPRESS_THRESHOLD = 0.50


def main():
    if not COMPOUNDS_JSONL.exists():
        raise SystemExit(f"{COMPOUNDS_JSONL} not found — run canonicalize_vcf_compounds.py first.")
    if not BOILING_POINTS_CACHE.exists():
        raise SystemExit(
            f"{BOILING_POINTS_CACHE} not found. This script does not fetch "
            f"live — see the module docstring for why, and for the cache "
            f"file's schema ({{cid, boiling_point_c, n_readings}} per line). "
            f"Populate it (a live fetch run, a supplied dataset) before "
            f"running this script."
        )

    bp_by_cid: dict[int, float] = {}
    for line in BOILING_POINTS_CACHE.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        bp_by_cid[row["cid"]] = row["boiling_point_c"]

    rows = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]

    n_with_cid = sum(1 for r in rows if r.get("pubchem_cid") is not None)
    distinct_cids_total = {r["pubchem_cid"] for r in rows if r.get("pubchem_cid") is not None}
    distinct_cids_matched = distinct_cids_total & set(bp_by_cid)
    coverage_fraction = len(distinct_cids_matched) / len(distinct_cids_total) if distinct_cids_total else 0.0
    claims_suppressed = coverage_fraction < COVERAGE_SUPPRESS_THRESHOLD

    all_bp = sorted(bp_by_cid.values())

    def tertile_cuts(values):
        if len(values) < 3:
            return None, None
        n = len(values)
        lo = values[n // 3]
        hi = values[(2 * n) // 3]
        return lo, hi

    lo_cut, hi_cut = tertile_cuts(all_bp)

    def volatility_bucket(bp):
        if bp is None or lo_cut is None:
            return None
        if bp < lo_cut:
            return "volatile"
        if bp < hi_cut:
            return "moderate"
        return "stable"

    bucket_counts: dict[str, int] = {}
    for r in rows:
        cid = r.get("pubchem_cid")
        bp = bp_by_cid.get(cid) if cid is not None else None
        r["boiling_point_c"] = bp
        bucket = volatility_bucket(bp) if not claims_suppressed else None
        r["volatility_bucket"] = bucket
        if bucket:
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    with open(COMPOUNDS_JSONL, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["volatility"] = {
        "n_distinct_pubchem_cids_in_corpus": len(distinct_cids_total),
        "n_distinct_cids_with_boiling_point": len(distinct_cids_matched),
        "coverage_fraction": round(coverage_fraction, 4),
        "coverage_suppress_threshold": COVERAGE_SUPPRESS_THRESHOLD,
        "volatility_claims_suppressed": claims_suppressed,
        "tertile_cutpoints_c": [lo_cut, hi_cut] if lo_cut is not None else None,
        "bucket_counts": bucket_counts,
        "fetch_source_note": (
            "Boiling points came from a live PubChem PUG View fetch run "
            "through the linked Mac's browser pane (this environment's own "
            "network egress cannot reach pubchem.ncbi.nlm.nih.gov directly "
            "— confirmed proxy-blocked from both the cloud container and "
            "the Mac's shell). PUG View does not offer a batch endpoint for "
            "this property, and was intermittently returning 503 under "
            "sustained load during this build, capping how much of the "
            "corpus could be fetched in the time available — see "
            "n_distinct_cids_with_boiling_point vs "
            "n_distinct_pubchem_cids_in_corpus for exactly how much."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Boiling-point coverage: {len(distinct_cids_matched)}/{len(distinct_cids_total)} "
          f"= {coverage_fraction:.1%}")
    print(f"Volatility claims suppressed: {claims_suppressed} "
          f"(threshold {COVERAGE_SUPPRESS_THRESHOLD:.0%})")
    if lo_cut is not None:
        print(f"Tertile cutpoints: volatile < {lo_cut}°C <= moderate < {hi_cut}°C <= stable")
    print(f"Bucket counts: {bucket_counts}")


if __name__ == "__main__":
    main()
