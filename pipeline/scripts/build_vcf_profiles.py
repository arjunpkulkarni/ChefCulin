"""
VCF Compound Layer — Step 4: build per-product compound profiles and
compute IDF over the culinary corpus.

Run from the repo root:  python pipeline/scripts/build_vcf_profiles.py

Reads:  pipeline/artifacts/vcf/step1_concat.parquet    (Step 1)
        pipeline/artifacts/vcf/vcf_product_parse.jsonl (Step 2)
        pipeline/artifacts/vcf/spine.jsonl              (Step 3)
        pipeline/artifacts/vcf/compounds.jsonl          (Step 3b)
Writes: pipeline/artifacts/vcf/profiles.jsonl
        pipeline/artifacts/vcf/compounds.jsonl   (rewritten in place, adds
                                                   df_culinary + idf per row)
        pipeline/artifacts/vcf/meta.json         (adds a "profiles" block)

"Product" here is the VCF raw product (one row per vcf_product_id — e.g.
"PEANUT (raw)" and "PEANUT (roasted)" are separate profiles), not the spine
entry. Step 5's pairing and Step 8's form diffs both need that granularity;
collapsing to spine level here would throw it away before it's ever used.

Per spec:
  profile[product] = set(compound_id)   -- canonical ids from Step 3b, so an
                                            "(=alias)" spelling and its
                                            partner don't count as two
                                            compounds in the same profile
  N                = count of CULINARY products (not all 584 — reference
                                            products are excluded from the
                                            corpus, per the Step 3 decision)
  df[compound]     = number of culinary profiles containing it
  idf[compound]    = ln(N / df[compound])

profile_source is "VCF" on every row — single source, no fallback, per
spec's explicit "one source per product profile" rule.

Sanity checks against the spec's 182-product sample (comparison only, the
full pull is a different — much larger — corpus and isn't expected to match
exactly): median/mean compounds per product, products with >=100 compounds,
distinct compounds, compounds in exactly one product, compounds in >=75% of
products, most ubiquitous compound. The one that's an actual gate, not just
a comparison: if any compound sits in >90% of culinary products, the spec
says the parse is wrong — this script raises rather than silently writing
output if that fires.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
STEP1_PARQUET = OUT_DIR / "step1_concat.parquet"
PARSE_JSONL = OUT_DIR / "vcf_product_parse.jsonl"
SPINE_JSONL = OUT_DIR / "spine.jsonl"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
PROFILES_JSONL = OUT_DIR / "profiles.jsonl"
META_JSON = OUT_DIR / "meta.json"

# Beef Ingestion Build Spec, Step 4 + Step 6: an external-source profile
# (produced by ingest_protein_beef.py) can carry compounds whose
# evidence_mode isn't "measured" — those count toward the profile's own
# membership (compound_ids, what a lens shows) but must NOT count toward
# document frequency/IDF (an inherited-once-per-family-member compound
# would inflate df and collapse its IDF weight for no real reason — see
# ingest_protein_beef.py's module docstring). VCF has no evidence_mode
# concept at all, so every VCF profile's df_eligible_compound_ids is just
# its compound_ids, unchanged — this is additive, not a behavior change
# for the existing corpus. If a future family's prebuilt file is present,
# it's merged in the same way; this script has no beef-specific logic,
# only a generic "external profile" merge point.
#
# 2026-08-30: this used to be an unconditional merge — if the file
# existed on disk, it silently joined the corpus, no flag, no log line
# calling it out. That nearly changed a VCF-only rebaseline's baseline
# (577/525 instead of 573/521) without anyone deciding it should, because
# nothing about running this script said "protein is included this time."
# James: needs a real guard, not a set-aside-the-file ritual someone has
# to remember. Fixed here with an explicit --include-protein flag,
# defaulting OFF — a run that includes external protein profiles has to
# say so on the command line, and a run that has protein files sitting on
# disk but doesn't pass the flag prints that fact loudly rather than
# staying silent about what it skipped.
EXTERNAL_PROFILES_DIR = REPO_ROOT / "pipeline" / "artifacts" / "protein"
EXTERNAL_PROFILE_FILES = [
    EXTERNAL_PROFILES_DIR / "beef_profiles_prebuilt.jsonl",
    EXTERNAL_PROFILES_DIR / "egg_profiles_prebuilt.jsonl",  # added 2026-08-30, egg ingestion
]

UBIQUITY_GATE = 0.90


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-protein",
        action="store_true",
        help=(
            "Merge external protein-family profile files (e.g. "
            "beef_profiles_prebuilt.jsonl) into the corpus. Default is OFF: "
            "a VCF-only run stays VCF-only even if those files are present "
            "on disk. Pass this explicitly to build the mixed corpus."
        ),
    )
    args = parser.parse_args()

    for p in (STEP1_PARQUET, PARSE_JSONL, SPINE_JSONL, COMPOUNDS_JSONL):
        if not p.exists():
            raise SystemExit(f"{p} not found — run the earlier steps first.")

    raw = pd.read_parquet(STEP1_PARQUET)
    products = [json.loads(l) for l in PARSE_JSONL.read_text().splitlines() if l.strip()]
    spine = [json.loads(l) for l in SPINE_JSONL.read_text().splitlines() if l.strip()]
    compound_rows = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]

    compound_id_by_raw = {r["raw_compound"]: r["compound_id"] for r in compound_rows}
    spine_id_by_product_id = {
        m["vcf_product_id"]: e["spine_id"]
        for e in spine
        for m in e["members"]
    }

    # raw VCF "Product" string -> set of canonical compound_ids
    compounds_by_raw_product: dict[str, set[str]] = defaultdict(set)
    for row in raw.itertuples(index=False):
        cid = compound_id_by_raw.get(row.Compound)
        if cid is None:
            raise SystemExit(
                f"Compound {row.Compound!r} has no entry in compounds.jsonl — "
                f"step1_concat.parquet and compounds.jsonl have drifted apart, "
                f"re-run canonicalize_vcf_compounds.py."
            )
        compounds_by_raw_product[row.Product].add(cid)

    profiles = []
    for p in products:
        cids = sorted(compounds_by_raw_product.get(p["raw_name"], set()))
        profiles.append(
            {
                "vcf_product_id": p["vcf_product_id"],
                "raw_name": p["raw_name"],
                "base_ingredient": p["base_ingredient"],
                "spine_id": spine_id_by_product_id[p["vcf_product_id"]],
                "class": p["class"],
                "product_group": p["product_group"],
                "profile_source": "VCF",
                "n_compounds": len(cids),
                "compound_ids": cids,
                "df_eligible_compound_ids": cids,  # VCF has no evidence_mode concept — everything counts
                "profile_size_class": "full",
            }
        )

    n_vcf_profiles = len(profiles)
    n_external_merged = 0
    external_sources_seen: set[str] = set()
    external_files_skipped: list[str] = []
    for ext_path in EXTERNAL_PROFILE_FILES:
        if not ext_path.exists():
            continue
        if not args.include_protein:
            external_files_skipped.append(str(ext_path))
            continue
        ext_profiles = [json.loads(l) for l in ext_path.read_text().splitlines() if l.strip()]
        for pr in ext_profiles:
            pr.setdefault("df_eligible_compound_ids", pr["compound_ids"])
            external_sources_seen.add(pr.get("profile_source", "UNKNOWN"))
        profiles.extend(ext_profiles)
        n_external_merged += len(ext_profiles)

    if external_files_skipped:
        print(
            f"NOTE: {len(external_files_skipped)} external protein profile "
            f"file(s) found on disk but NOT merged (pass --include-protein "
            f"to include them): {external_files_skipped}"
        )

    with open(PROFILES_JSONL, "w") as f:
        for pr in profiles:
            f.write(json.dumps(pr, ensure_ascii=False) + "\n")

    # --- IDF, over the culinary corpus only ---
    culinary = [pr for pr in profiles if pr["class"] == "culinary"]
    N = len(culinary)
    df: Counter = Counter()
    for pr in culinary:
        for cid in pr["df_eligible_compound_ids"]:
            df[cid] += 1
    idf = {cid: math.log(N / count) for cid, count in df.items()}

    for r in compound_rows:
        cid = r["compound_id"]
        r["df_culinary"] = df.get(cid, 0)
        r["idf"] = idf.get(cid)
    with open(COMPOUNDS_JSONL, "w") as f:
        for r in compound_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- sanity checks (spec Step 4, compared against the 182-product sample) ---
    sizes = [pr["n_compounds"] for pr in culinary]
    sizes_sorted = sorted(sizes)
    n = len(sizes_sorted)
    median = (
        sizes_sorted[n // 2]
        if n % 2
        else (sizes_sorted[n // 2 - 1] + sizes_sorted[n // 2]) / 2
    )
    mean = sum(sizes) / n
    ge_100 = sum(1 for s in sizes if s >= 100)
    n_distinct_compounds_culinary = len(df)
    n_exactly_one = sum(1 for c in df.values() if c == 1)
    most_ubiquitous_cid, most_ubiquitous_df = df.most_common(1)[0]
    most_ubiquitous_frac = most_ubiquitous_df / N
    ge_75pct = sum(1 for c in df.values() if c / N >= 0.75)

    if most_ubiquitous_frac > UBIQUITY_GATE:
        raise SystemExit(
            f"GATE FAILED: compound_id {most_ubiquitous_cid} appears in "
            f"{most_ubiquitous_df}/{N} culinary products ({most_ubiquitous_frac:.1%}) "
            f"— over the spec's {UBIQUITY_GATE:.0%} threshold. Per spec: 'the parse "
            f"is wrong' — most likely a product-name collision collapsing many "
            f"products into one. Not writing profiles/meta — investigate before "
            f"re-running."
        )

    most_ubiquitous_raw = next(
        (r["raw_compound"] for r in compound_rows if r["compound_id"] == most_ubiquitous_cid),
        most_ubiquitous_cid,
    )

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["profiles"] = {
        "n_profiles_total": len(profiles),
        "n_profiles_vcf_source": n_vcf_profiles,
        "n_profiles_external_source_merged": n_external_merged,
        "external_profile_sources_seen": sorted(external_sources_seen),
        "include_protein_flag_passed": args.include_protein,
        "external_protein_files_present_but_skipped": external_files_skipped,
        "n_profiles_culinary": N,
        "n_profiles_reference": len(profiles) - N,
        "median_compounds_per_product": median,
        "mean_compounds_per_product": round(mean, 1),
        "products_with_ge_100_compounds": f"{ge_100} of {N}",
        "distinct_compounds_culinary": n_distinct_compounds_culinary,
        "compounds_in_exactly_one_product": n_exactly_one,
        "compounds_in_ge_75pct_products": ge_75pct,
        "most_ubiquitous_compound": {
            "compound_id": most_ubiquitous_cid,
            "raw_compound": most_ubiquitous_raw,
            "n_products": most_ubiquitous_df,
            "of_products": N,
            "fraction": round(most_ubiquitous_frac, 4),
        },
        "ubiquity_gate_threshold": UBIQUITY_GATE,
        "sample_comparison_182_products": {
            "median": 87, "mean": 123, "ge_100_of_182": 80,
            "distinct_compounds": 4733, "exactly_one_product": 2476,
            "most_ubiquitous": "1-hexanol, 108/182 (59%)", "ge_75pct": 0,
        },
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {len(profiles)} profiles ({N} culinary, {len(profiles)-N} reference) to {PROFILES_JSONL}")
    print(f"Culinary corpus N = {N}")
    print(f"Median compounds/product: {median}  (sample: 87)")
    print(f"Mean: {mean:.1f}  (sample: 123)")
    print(f"Products with >=100 compounds: {ge_100} of {N}  (sample: 80 of 182)")
    print(f"Distinct compounds (culinary): {n_distinct_compounds_culinary}  (sample: 4733)")
    print(f"Compounds in exactly one product: {n_exactly_one}  (sample: 2476)")
    print(f"Most ubiquitous: {most_ubiquitous_raw} ({most_ubiquitous_cid}) "
          f"{most_ubiquitous_df}/{N} = {most_ubiquitous_frac:.1%}  (sample: 1-hexanol, 59%)")
    print(f"Compounds in >=75% of products: {ge_75pct}  (sample: 0)")


if __name__ == "__main__":
    main()
