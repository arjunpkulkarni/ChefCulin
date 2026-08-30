"""
VCF Compound Layer — Step 3: derive the ingredient spine and freeze the
vocabulary that Step 4 (IDF) computes over.

Run from the repo root:  python pipeline/scripts/build_vcf_spine.py

Reads:  pipeline/artifacts/vcf/vcf_product_parse.jsonl   (Step 2 output)
Writes: pipeline/artifacts/vcf/spine.jsonl
        pipeline/artifacts/vcf/meta.json                 (adds a "spine" block)

Per the spec, the spine falls out of Step 2 rather than being assembled
separately:
  1. Group products by base_ingredient. Each distinct base becomes a spine
     entry, keyed by a CulinAI-owned id ("culin:hazelnut") rather than a
     VCF or FooDB id, so the spine doesn't move when either of those does.
  2. Attach aliases (union of every member's aliases) so "filbert" or
     "bell pepper" resolves to the right entry.
  3. class (culinary|reference) is carried through from Step 2 as-is —
     that tagging is already final as of the Step 3 correction landed in
     parse_vcf_products.py (Pistacia atlantica/palaestina).
  4. Freeze and version the resulting product list — recorded below as a
     content hash over (vcf_product_id, raw_name, base_ingredient, class),
     so any future change to the parse (a fix, a re-pull) is detectable
     rather than silently shifting every downstream weight.

`policy` (single|expand|category, Step 9) is intentionally left null here.
Which policy applies to a multi-member entry is not a mechanical function
of member count — it depends on whether the members are meaningfully
different culinary states (nine pork products: ask which one) or
functionally the same thing under different lab conditions (three rum
volatility tiers: safe to range over) — and the spec is explicit that
resolution must be "a deterministic lookup, never a model decision." That
call belongs to Step 9, not invented here — see
build_vcf_resolution_policy.py, which must run AFTER this script (it reads
spine.jsonl and rewrites it in place, filling in `policy` plus
`default_member`/`resolution_confidence`; every rerun of this script
resets `policy` to null, so a full pipeline rebuild needs both scripts in
that order).

Order matters: this step decides which products count as "the vocabulary"
before Step 4 computes IDF over it. Per spec, exclude class=="reference"
from that corpus — recorded in meta.json so Step 4 doesn't have to
re-derive the same decision.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
PARSE_JSONL = OUT_DIR / "vcf_product_parse.jsonl"
SPINE_JSONL = OUT_DIR / "spine.jsonl"
META_JSON = OUT_DIR / "meta.json"


def slugify(base_ingredient: str) -> str:
    s = base_ingredient.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def build_spine(products: list[dict]) -> list[dict]:
    by_base: dict[str, list[dict]] = defaultdict(list)
    for p in products:
        by_base[p["base_ingredient"]].append(p)

    entries = []
    for base_ingredient, members in sorted(by_base.items()):
        groups = sorted({m["product_group"] for m in members})
        if len(groups) != 1:
            # Verified absent in the 584-product corpus as of this run; if a
            # future re-pull introduces one, surface it rather than silently
            # picking a group.
            raise ValueError(
                f"base_ingredient {base_ingredient!r} spans multiple "
                f"product_group values: {groups} — needs a human call, "
                f"not a default."
            )

        aliases = sorted({a for m in members for a in m["aliases"]})
        class_counts: dict[str, int] = defaultdict(int)
        for m in members:
            class_counts[m["class"]] += 1

        entries.append(
            {
                "spine_id": f"culin:{slugify(base_ingredient)}",
                "display_name": base_ingredient.capitalize(),
                "base_ingredient": base_ingredient,
                "aliases": aliases,
                "product_group": groups[0],
                "n_members": len(members),
                "class_counts": dict(class_counts),
                "policy": None,  # Step 9 — resolution policy, not decided here
                "members": [
                    {
                        "vcf_product_id": m["vcf_product_id"],
                        "raw_name": m["raw_name"],
                        "class": m["class"],
                        "preparation": m["preparation"],
                        "cure_state": m["cure_state"],
                        "state": m["state"],
                        "form": m["form"],
                        "cultivar": m["cultivar"],
                        "binomial": m["binomial"],
                    }
                    for m in members
                ],
            }
        )
    return entries


def vocabulary_hash(products: list[dict]) -> str:
    rows = sorted(
        (p["vcf_product_id"], p["raw_name"], p["base_ingredient"], p["class"])
        for p in products
    )
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main():
    if not PARSE_JSONL.exists():
        raise SystemExit(f"{PARSE_JSONL} not found — run parse_vcf_products.py first.")

    products = [json.loads(line) for line in PARSE_JSONL.read_text().splitlines() if line.strip()]
    still_flagged = [p for p in products if p["needs_review"]]
    if still_flagged:
        raise SystemExit(
            f"{len(still_flagged)} product(s) still needs_review=True — "
            f"resolve those before deriving the spine (order isn't cheaply "
            f"reversible per the spec)."
        )

    entries = build_spine(products)

    with open(SPINE_JSONL, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    culinary_products = [p for p in products if p["class"] == "culinary"]
    reference_products = [p for p in products if p["class"] == "reference"]
    multi_member = [e for e in entries if e["n_members"] > 1]
    pure_reference_entries = [e for e in entries if e["class_counts"].get("culinary", 0) == 0]
    mixed_class_entries = [e for e in entries if len(e["class_counts"]) > 1]

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["spine"] = {
        "n_spine_entries": len(entries),
        "n_products_total": len(products),
        "n_products_culinary": len(culinary_products),
        "n_products_reference": len(reference_products),
        "n_multi_member_entries": len(multi_member),
        "n_pure_reference_entries": len(pure_reference_entries),
        "n_mixed_class_entries": len(mixed_class_entries),
        "idf_corpus": "culinary",  # Step 4 sanity: exclude reference, per spec recommendation
        "vocabulary_version": "vcf_spine_v1",
        "vocabulary_hash": vocabulary_hash(products),
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {len(entries)} spine entries to {SPINE_JSONL}")
    print(f"  {len(multi_member)} entries have >1 VCF product member")
    print(f"  {len(pure_reference_entries)} entries are reference-only")
    print(f"  {len(mixed_class_entries)} entries mix culinary + reference members: "
          f"{[e['base_ingredient'] for e in mixed_class_entries]}")
    print(f"Culinary products (IDF corpus, Step 4): {len(culinary_products)} of {len(products)}")


if __name__ == "__main__":
    main()
