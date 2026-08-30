"""
VCF Compound Layer — Step 7: quantity fields, stored but never scored.

Run from the repo root:  python pipeline/scripts/build_vcf_quantities.py

Reads:  pipeline/artifacts/vcf/step1_concat.parquet    (Step 1, raw rows)
        pipeline/artifacts/vcf/vcf_product_parse.jsonl (Step 2, product ids)
        pipeline/artifacts/vcf/spine.jsonl              (Step 3, spine ids)
        pipeline/artifacts/vcf/compounds.jsonl          (Step 3b, canonical ids)
Writes: pipeline/artifacts/vcf/quantities.jsonl
        pipeline/artifacts/vcf/meta.json  (adds a "quantities" block)

Per spec: only ~44% of the sample's rows carried a usable quantity bound,
and the bounds that exist mix real numbers with censored/qualitative
literals ("<0.01", "trace", "Present"). A pair scored with quantity
weighting is not comparable to one scored without, so v1 is presence/
absence only — this script stores the quantity fields at full (product,
compound) granularity for later use, and does not feed them into Step 5's
score or Step 4's IDF in any way. Nothing here is read by build_vcf_pairs.py
or build_vcf_profiles.py; this is purely an additive side table keyed the
same way profiles.jsonl is (vcf_product_id, compound_id) so the two can be
joined later without re-deriving anything.

Granularity is the original CSV row, not the deduplicated compound_ids set
that profiles.jsonl builds. 457 of 66,727 distinct (Product, compound_id)
pairs in the full pull have more than one raw row — mostly stereoisomer
spellings (e.g. two named cadinene isomers) that canonicalize to the same
compound_id in Step 3b. Both raw rows are kept here rather than merged:
profiles.jsonl already collapsed this to the single presence bit that
scoring needs, and inventing an aggregation rule for quantity bounds (max?
sum? first?) isn't something the spec asked for and isn't needed for v1 —
storing what VCF actually reported, once per row, is the flag-don't-guess
choice.

Literal parsing, by inspection of the full pull's actual value set (53,801
non-empty bound strings across both columns):
  ""                    -> kind "missing"     (no bound reported)
  "<0.01", "<2E-006", … -> kind "censored"     (below this numeric threshold;
                                                 the true value is unknown,
                                                 not the threshold itself, so
                                                 quantity_*_value is null and
                                                 the threshold is kept in
                                                 quantity_*_threshold)
  "trace"               -> kind "trace"        (qualitative, no threshold)
  "Present"             -> kind "present"      (qualitative, no threshold)
  a plain number         -> kind "numeric"      (quantity_*_value set)
  anything else           -> kind "unparsed"    (kept verbatim, flagged loudly
                                                 rather than silently dropped
                                                 — see the assertion in main)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
STEP1_PARQUET = OUT_DIR / "step1_concat.parquet"
PARSE_JSONL = OUT_DIR / "vcf_product_parse.jsonl"
SPINE_JSONL = OUT_DIR / "spine.jsonl"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
QUANTITIES_JSONL = OUT_DIR / "quantities.jsonl"
META_JSON = OUT_DIR / "meta.json"

CENSORED_RE = re.compile(r"^<\s*([\d.eE+\-]+)$")

# Traced 2026-08-28: one row in 28000_29000.csv — DATE (Phoenix dactylifera
# L.) x carvone (=p-6,8-menthadien-2-one) — has an unquoted comma inside its
# Compound Group value ("Carbonyls, ketones" written without the quotes
# every other occurrence of this same compound group uses). That shifts the
# rest of the row one field early: "Carbonyls" lands in Compound Group,
# ' ketones"' lands in Quantity Lower Bound, and Quantity Upper Bound is
# empty. This is not a real quantity value — it's a fragment of the group
# name — so it's treated as "missing" here, not "unparsed". (Compound Group
# itself needs no fix: canonicalize_vcf_compounds.py's group_by_compound
# takes a majority vote across all 105 occurrences of this compound name,
# and 104 of them already say "Carbonyls, ketones" correctly, so the
# truncated value from this one row is already outvoted.)
KNOWN_CSV_ARTIFACT_VALUES = {'ketones"'}


def parse_bound(raw) -> dict:
    s = "" if raw is None else str(raw).strip()
    if s == "" or s in KNOWN_CSV_ARTIFACT_VALUES:
        return {"raw": None, "value": None, "threshold": None, "kind": "missing"}
    m = CENSORED_RE.match(s)
    if m:
        try:
            threshold = float(m.group(1))
        except ValueError:
            return {"raw": s, "value": None, "threshold": None, "kind": "unparsed"}
        return {"raw": s, "value": None, "threshold": threshold, "kind": "censored"}
    if s.lower() == "trace":
        return {"raw": s, "value": None, "threshold": None, "kind": "trace"}
    if s.lower() == "present":
        return {"raw": s, "value": None, "threshold": None, "kind": "present"}
    try:
        value = float(s)
        return {"raw": s, "value": value, "threshold": None, "kind": "numeric"}
    except ValueError:
        return {"raw": s, "value": None, "threshold": None, "kind": "unparsed"}


def main():
    for p in (STEP1_PARQUET, PARSE_JSONL, SPINE_JSONL, COMPOUNDS_JSONL):
        if not p.exists():
            raise SystemExit(f"{p} not found — run the earlier steps first.")

    raw = pd.read_parquet(STEP1_PARQUET)
    products = [json.loads(l) for l in PARSE_JSONL.read_text().splitlines() if l.strip()]
    spine = [json.loads(l) for l in SPINE_JSONL.read_text().splitlines() if l.strip()]
    compound_rows = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]

    product_id_by_raw_name = {p["raw_name"]: p["vcf_product_id"] for p in products}
    spine_id_by_product_id = {
        m["vcf_product_id"]: e["spine_id"] for e in spine for m in e["members"]
    }
    compound_id_by_raw = {r["raw_compound"]: r["compound_id"] for r in compound_rows}

    rows = []
    kind_counts: Counter = Counter()
    unparsed_examples: list[str] = []
    n_known_csv_artifacts = 0

    for r in raw.itertuples(index=False):
        pid = product_id_by_raw_name.get(r.Product)
        if pid is None:
            raise SystemExit(
                f"Product {r.Product!r} has no entry in vcf_product_parse.jsonl — "
                f"step1_concat.parquet and Step 2 have drifted apart, re-run "
                f"parse_vcf_products.py."
            )
        cid = compound_id_by_raw.get(r.Compound)
        if cid is None:
            raise SystemExit(
                f"Compound {r.Compound!r} has no entry in compounds.jsonl — "
                f"re-run canonicalize_vcf_compounds.py."
            )
        raw_lower_str = "" if r._5 is None else str(r._5).strip()
        raw_upper_str = "" if r._6 is None else str(r._6).strip()
        if raw_lower_str in KNOWN_CSV_ARTIFACT_VALUES:
            n_known_csv_artifacts += 1
        if raw_upper_str in KNOWN_CSV_ARTIFACT_VALUES:
            n_known_csv_artifacts += 1
        lower = parse_bound(r._5)  # "Quantity Lower Bound"
        upper = parse_bound(r._6)  # "Quantity Upper Bound"
        kind_counts[lower["kind"]] += 1
        kind_counts[upper["kind"]] += 1
        if lower["kind"] == "unparsed" and len(unparsed_examples) < 20:
            unparsed_examples.append(raw_lower_str)
        if upper["kind"] == "unparsed" and len(unparsed_examples) < 20:
            unparsed_examples.append(raw_upper_str)

        rows.append(
            {
                "vcf_product_id": pid,
                "raw_name": r.Product,
                "spine_id": spine_id_by_product_id.get(pid),
                "compound_id": cid,
                "raw_compound": r.Compound,
                "quantity_lower_raw": lower["raw"],
                "quantity_lower_value": lower["value"],
                "quantity_lower_threshold": lower["threshold"],
                "quantity_lower_kind": lower["kind"],
                "quantity_upper_raw": upper["raw"],
                "quantity_upper_value": upper["value"],
                "quantity_upper_threshold": upper["threshold"],
                "quantity_upper_kind": upper["kind"],
                "has_quantity": lower["kind"] != "missing" or upper["kind"] != "missing",
            }
        )

    if unparsed_examples:
        raise SystemExit(
            f"{kind_counts['unparsed']} quantity bound values did not match any "
            f"known literal shape (numeric, '<N' censored, 'trace', 'Present'). "
            f"Examples: {unparsed_examples}. Per spec's flag-don't-guess rule, "
            f"stopping rather than silently writing these as null — add a case "
            f"to parse_bound() once the shape is known."
        )

    with open(QUANTITIES_JSONL, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_rows = len(rows)
    n_with_lower = sum(1 for r in rows if r["quantity_lower_kind"] != "missing")
    n_with_upper = sum(1 for r in rows if r["quantity_upper_kind"] != "missing")
    n_with_either = sum(1 for r in rows if r["has_quantity"])

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["quantities"] = {
        "n_rows": n_rows,
        "n_with_lower_bound": n_with_lower,
        "n_with_upper_bound": n_with_upper,
        "n_with_either_bound": n_with_either,
        "fraction_with_either_bound": round(n_with_either / n_rows, 4),
        "sample_comparison_fraction_with_bound": 0.44,
        "bound_literal_kind_counts": dict(kind_counts),
        "n_known_csv_artifacts_corrected": n_known_csv_artifacts,
        "known_csv_artifacts_note": (
            "1 row (DATE x carvone, 28000_29000.csv line 107) has an unquoted "
            "comma in its Compound Group value, shifting a 'Carbonyls, ketones' "
            "fragment into Quantity Lower Bound as literal 'ketones\"'. Treated "
            "as missing, not a real value — see KNOWN_CSV_ARTIFACT_VALUES."
        ),
        "scored_on": False,
        "note": (
            "v1 per spec: presence/absence only. These fields are stored for "
            "future use and are not read by build_vcf_profiles.py (IDF) or "
            "build_vcf_pairs.py (pairing score) — mixing quantity-weighted and "
            "unweighted scores would rank on two silently different scales."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {n_rows} quantity rows to {QUANTITIES_JSONL}")
    print(f"Rows with a lower bound: {n_with_lower} ({n_with_lower/n_rows:.1%})")
    print(f"Rows with an upper bound: {n_with_upper} ({n_with_upper/n_rows:.1%})")
    print(f"Rows with either bound: {n_with_either} ({n_with_either/n_rows:.1%})  (sample: 44%)")
    print(f"Bound literal kinds: {dict(kind_counts)}")


if __name__ == "__main__":
    main()
