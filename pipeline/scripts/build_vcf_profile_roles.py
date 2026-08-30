"""
VCF Compound Layer — precompute role scores onto profiles.jsonl.

Run from the repo root, AFTER build_vcf_profiles.py and
build_vcf_compound_roles.py:
    python pipeline/scripts/build_vcf_profile_roles.py

Reads:  pipeline/artifacts/vcf/profiles.jsonl
        pipeline/artifacts/vcf/compound_roles.jsonl
Writes: pipeline/artifacts/vcf/profiles.jsonl   (rewritten in place, adds
                                                  role_counts + role_shares)
        pipeline/artifacts/vcf/meta.json        (adds a "profile_roles" block)

Per review: "Store on every row of profiles.jsonl: role_counts, role_shares
... Computed once per product (573) rather than per pair (7,741) — roughly
a 13x reduction in trigger-time work, and it makes every role score
inspectable in the artifact rather than recomputed inside an evaluator."

--- Share definition, validated against the review's own numbers ---

role_share = role_count / len(profile's full compound_ids list) — the
WHOLE profile, not restricted to compounds that carry a phase_bucket and
compound_group. This was checked directly against the review's own
CUTTLEFISH (13 markers / 68.4%) and PORK, UNCURED (smoked) (10 markers /
38.5%) figures before writing this script: len(compound_ids) for those two
products is 19 and 26 respectively, and 13/19 = 0.684, 10/26 = 0.385 —
exact matches. Restricting the denominator to bucket-and-group-valid
compounds only (as Step 11e's own group_share_in_profile does) gives
72.2%/41.7% instead, which does NOT match — so this script deliberately
uses a different, simpler denominator than group_share_in_profile, because
that's what reproduces the reviewed numbers.

Every role currently defined in compound_roles.jsonl gets a count/share
entry on every profile, including roles with zero occurrences (0 / 0.0,
not an absent key) — a future consumer checking role_shares["some_role"]
should never need to distinguish "zero" from "not computed."
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
PROFILES_JSONL = OUT_DIR / "profiles.jsonl"
COMPOUND_ROLES_JSONL = OUT_DIR / "compound_roles.jsonl"
META_JSON = OUT_DIR / "meta.json"


def main():
    for p in (PROFILES_JSONL, COMPOUND_ROLES_JSONL):
        if not p.exists():
            raise SystemExit(f"{p} not found — run the earlier pipeline steps first.")

    profiles = [json.loads(l) for l in PROFILES_JSONL.read_text().splitlines() if l.strip()]
    role_rows = [json.loads(l) for l in COMPOUND_ROLES_JSONL.read_text().splitlines() if l.strip()]

    all_roles = sorted({r["role"] for r in role_rows})
    role_ids_by_role = {role: {r["compound_id"] for r in role_rows if r["role"] == role} for role in all_roles}

    n_products_with_role_above_threshold = Counter()  # informational only, no threshold applied here

    for prof in profiles:
        cids = prof["compound_ids"]
        n_total = len(cids)
        counts = {}
        shares = {}
        for role in all_roles:
            ids = role_ids_by_role[role]
            n = sum(1 for c in cids if c in ids)
            counts[role] = n
            shares[role] = round(n / n_total, 4) if n_total else 0.0
        prof["role_counts"] = counts
        prof["role_shares"] = shares

    with open(PROFILES_JSONL, "w") as f:
        for prof in profiles:
            f.write(json.dumps(prof, ensure_ascii=False) + "\n")

    # Coverage: how many culinary products carry each role at all (count > 0).
    culinary = [p for p in profiles if p.get("class") == "culinary"]
    role_presence = {
        role: sum(1 for p in culinary if p["role_counts"][role] > 0) for role in all_roles
    }

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["profile_roles"] = {
        "roles": all_roles,
        "n_culinary_products": len(culinary),
        "n_culinary_products_with_role_present": role_presence,
        "share_definition": "role_count / len(profile.compound_ids) — the WHOLE profile, unrestricted",
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Added role_counts/role_shares to {len(profiles)} profiles for roles: {all_roles}")
    for role in all_roles:
        print(f"  {role:<24} present in {role_presence[role]}/{len(culinary)} culinary products")


if __name__ == "__main__":
    main()
