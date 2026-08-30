"""
VCF Compound Layer — Steps 5 & 6: IDF-weighted cosine pairing score, with
the shared-compound explanation persisted alongside it (the two are one
deliverable per spec — pairs.jsonl — and computing the score's numerator
already requires the shared-compound set the explanation needs).

Run from the repo root:  python pipeline/scripts/build_vcf_pairs.py

Reads:  pipeline/artifacts/vcf/profiles.jsonl    (Step 4)
        pipeline/artifacts/vcf/compounds.jsonl   (Step 3b/4, has idf)
Writes: pipeline/artifacts/vcf/pairs.jsonl
        pipeline/artifacts/vcf/meta.json  (adds a "pairs" block)

score(a,b) = sum(idf[c]^2 for c in shared) / (norm(a) * norm(b))
  where norm(x) = sqrt(sum(idf[c]^2 for c in profile(x)))

Computed over culinary profiles only (532) — reference profiles were never
part of the IDF corpus and pairing them wouldn't mean anything relative to
weights computed without them.

Same-spine_id pairs are excluded (PEANUT raw vs. PEANUT roasted never
"pair" with each other) — that's Step 8's job (form diffs), and the
existing compound_network.py already draws this line with its own
is_same_base() for the same reason: comparing an ingredient with itself
under another prep state isn't a pairing suggestion.

pairs.jsonl stores each product's top 20 matches (directed: anchor -> a
ranked list), not the full ~141k possible unordered pairs among 532
products — the spec's own hub-check works off "every product's top-10", so
that's the actual query pattern this needs to serve, not an exhaustive
matrix. The full O(n^2) score is still computed once per unordered pair
(each pair contributes to both endpoints' ranked lists), just not all of
it is persisted.

Validation gates from the spec, run before writing anything:
  - Coffee's top matches should include roasted hazelnut, roasted peanut,
    cocoa liquor, roasted cocoa beans, and popcorn (a 72-compound profile
    that raw count or Jaccard would bury under bigger ones). If coffee's
    top-20 comes back beverages instead, the weighting isn't doing its job
    and this script stops rather than writing bad output.
  - Hub check: no product should occupy more than ~40% of all products'
    top-10 lists. This one is reported, not a hard stop — the spec frames
    it as a diagnostic ("the metric is not controlling for size"), not the
    same kind of "the parse is wrong" gate as Step 4's ubiquity check.

--- Post-Ingestion Fixes, Fix 3: near-duplicate suppression ---

28.6% of anchors (149 of 521) have a top-1 match sharing >=85% of the
anchor's own compound set — VACCINIUM SPECIES/BILBERRY, WINE/{RED,WHITE,
PORT} WINE, WHISKY/{MALT,SCOTCH} WHISKY, HONEY/{DANDELION,LONGAN} HONEY —
genus-vs-species or generic-vs-variant entries that the SPINE layer never
clustered together. That inflated the reported VCF median top-1 score from
an honest 0.26 to 0.32, and for a chef it's worse than a scoring artifact:
the lens's single best recommendation for `tomato` or `milk` is
functionally the same ingredient again.

Every row gets a `suppressed_reason` field (kept, never deleted, per
James's instruction that this be auditable/reversible): non-null only when
BOTH (1) shared_count/anchor's own n_compounds >= 0.85, AND (2) the match
shares the anchor's OWN spine_id. Condition 2 turns out to be a no-op
against this corpus's actual data — see the `near_duplicate_suppression`
meta.json block's `finding` for why (the short version: candidate
generation, above, already excludes same-spine_id pairs entirely, so
nothing that reaches this file can ever satisfy "same spine_id as the
anchor" — the near-duplicates condition 2 was meant to confirm are, by
construction, always DIFFERENT spine_ids). Reported as a finding, not
silently patched to a different criterion — the corrected approach needs a
genus/species/name-variant match at the spine layer, which is a bigger
change than this pass and is James's call.
"""
from __future__ import annotations

import itertools
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[2] / "pipeline" / "artifacts" / "vcf"
PROFILES_JSONL = OUT_DIR / "profiles.jsonl"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
PAIRS_JSONL = OUT_DIR / "pairs.jsonl"
META_JSON = OUT_DIR / "meta.json"

TOP_K_STORED = 20
TOP_K_HUB_CHECK = 10
HUB_WARN_THRESHOLD = 0.40
TOP_N_EXPLANATION_COMPOUNDS = 5

# Post-Ingestion Fixes, Fix 3: suppress a match at the display/ranking
# layer (never delete the row — see NEAR_DUP_SUPPRESSED_REASON below) when
# BOTH hold: (1) the match covers >= this fraction of the ANCHOR's own
# compound set, and (2) the match resolves to the SAME spine_id as the
# anchor. Two conditions, not one — overlap alone would also catch
# genuinely similar but distinct products (IRISH WHISKEY/CANADIAN WHISKY
# share 87.5% of Irish whiskey's compounds and are not the same product;
# LOBSTER/PRAWN share 100% of lobster's smaller profile and are different
# animals). See main()'s suppression block for why condition 2, AS
# SPECIFIED, cannot currently suppress anything in this corpus.
NEAR_DUP_OVERLAP_THRESHOLD = 0.85
NEAR_DUP_SUPPRESSED_REASON = "near_duplicate_same_spine"

# Step 5's own validation target — checked against coffee's stored top-20.
COFFEE_RAW_NAME = "COFFEE"
EXPECTED_COFFEE_MATCHES = {
    "hazelnut (roasted)": "FILBERT, HAZELNUT (roasted)",
    "peanut (roasted)": "PEANUT (roasted)",
    "cocoa liquor": "COCOA LIQUOR",
    "roasted cocoa beans": "ROASTED COCOA BEANS",
    "popcorn": "POPCORN",
}


def main():
    if not PROFILES_JSONL.exists() or not COMPOUNDS_JSONL.exists():
        raise SystemExit("profiles.jsonl / compounds.jsonl not found — run the earlier steps first.")

    profiles = [json.loads(l) for l in PROFILES_JSONL.read_text().splitlines() if l.strip()]
    compound_rows = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]
    compound_meta = {r["compound_id"]: r for r in compound_rows}  # last row per id wins; idf is constant across dupes

    # NOTE: sums below always run over a *sorted* sequence of compound_ids,
    # never a bare set. Python randomizes str hash (and therefore set
    # iteration order) per process by default, and float addition is not
    # associative — summing the same idf_sq values in a different order
    # produces a different (if tiny) rounding result. Found by running this
    # script twice on identical input and seeing hub-check counts drift by
    # +/-1: two near-tied candidates flipped rank at the boundary. Sorting
    # first makes every run byte-identical given the same input, matching
    # the spec's reproducibility expectations elsewhere (the frozen,
    # hashed spine vocabulary; deterministic policy lookups).
    culinary = [p for p in profiles if p["class"] == "culinary"]
    sets = {p["vcf_product_id"]: set(p["compound_ids"]) for p in culinary}
    idf = {cid: (compound_meta[cid]["idf"] or 0.0) for cid in {c for p in culinary for c in p["compound_ids"]}}
    idf_sq = {cid: v * v for cid, v in idf.items()}
    norms = {
        pid: math.sqrt(sum(idf_sq.get(c, 0.0) for c in sorted(cset)))
        for pid, cset in sets.items()
    }

    by_id = {p["vcf_product_id"]: p for p in culinary}
    candidates: dict[int, list[dict]] = defaultdict(list)

    for a, b in itertools.combinations(culinary, 2):
        if a["spine_id"] == b["spine_id"]:
            continue
        pa, pb = a["vcf_product_id"], b["vcf_product_id"]
        shared = sets[pa] & sets[pb]
        if not shared:
            continue
        numerator = sum(idf_sq.get(c, 0.0) for c in sorted(shared))
        denom = norms[pa] * norms[pb]
        score = numerator / denom if denom > 0 else 0.0
        entry_ab = {"other_id": pb, "score": score, "shared": shared}
        entry_ba = {"other_id": pa, "score": score, "shared": shared}
        candidates[pa].append(entry_ab)
        candidates[pb].append(entry_ba)

    def explain(shared_ids: set) -> tuple[list[dict], list[dict]]:
        # Sort the set into a list first (see note above) so idf ties break
        # on compound_id, not on hash-randomized set iteration order.
        shared_sorted = sorted(shared_ids)
        ranked = sorted(shared_sorted, key=lambda c: idf.get(c, 0.0), reverse=True)
        top_compounds = [
            {
                "compound_id": c,
                "raw_compound": compound_meta[c]["raw_compound"],
                "compound_group": compound_meta[c]["compound_group"],
                "df_culinary": compound_meta[c]["df_culinary"],
                "idf": idf.get(c, 0.0),
            }
            for c in ranked[:TOP_N_EXPLANATION_COMPOUNDS]
        ]
        group_scores: Counter = Counter()
        for c in shared_sorted:
            group_scores[compound_meta[c]["compound_group"]] += idf_sq.get(c, 0.0)
        # most_common() ties break on insertion order, which is now fixed
        # since group_scores was built from a sorted sequence above; add an
        # explicit secondary key (group name) for full determinism anyway.
        ranked_groups = sorted(group_scores.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        top_groups = [
            {"compound_group": g, "n_shared": sum(1 for c in shared_sorted if compound_meta[c]["compound_group"] == g),
             "sum_idf_sq": s}
            for g, s in ranked_groups
        ]
        return top_compounds, top_groups

    pair_rows = []
    top10_occupants: Counter = Counter()
    for pid, cands in candidates.items():
        # One slot per spine_id, not per product. Pairing is computed at
        # individual-product granularity (raw vs. roasted hazelnut can and
        # do score differently against coffee, and Step 8 needs that), but
        # a chef-facing "top matches" list shouldn't spend two of its slots
        # on "hazelnut (roasted)" and "hazelnut (raw species name)" — that
        # reads as a bug, not as two distinct pairing ideas. Keep the
        # best-scoring product per match spine_id, then rank over that.
        best_per_spine: dict[str, dict] = {}
        for c in cands:
            sid = by_id[c["other_id"]]["spine_id"]
            if sid not in best_per_spine or c["score"] > best_per_spine[sid]["score"]:
                best_per_spine[sid] = c
        cands = sorted(best_per_spine.values(), key=lambda e: (-e["score"], e["other_id"]))
        top = cands[:TOP_K_STORED]
        anchor = by_id[pid]
        for rank, c in enumerate(top, start=1):
            other = by_id[c["other_id"]]
            top_compounds, top_groups = explain(c["shared"])
            pair_rows.append(
                {
                    "anchor_vcf_product_id": pid,
                    "anchor_raw_name": anchor["raw_name"],
                    "anchor_spine_id": anchor["spine_id"],
                    "match_vcf_product_id": other["vcf_product_id"],
                    "match_raw_name": other["raw_name"],
                    "match_spine_id": other["spine_id"],
                    "rank": rank,
                    "score": c["score"],
                    "shared_count": len(c["shared"]),
                    "top_shared_compounds": top_compounds,
                    "shared_compound_groups": top_groups,
                }
            )
            if rank <= TOP_K_HUB_CHECK:
                top10_occupants[c["other_id"]] += 1

    # --- Post-Ingestion Fixes, Fix 3: near-duplicate suppression ---
    # Applied at the display/ranking layer only — every row stays in the
    # file (rank/score/shared_count untouched); a suppressed row gains
    # `suppressed_reason`, everything else gets `suppressed_reason: None`.
    spine_by_id = {p["vcf_product_id"]: p["spine_id"] for p in culinary}
    n_compounds_by_id = {p["vcf_product_id"]: p["n_compounds"] for p in culinary}
    n_suppressed = 0
    anchors_with_suppression: dict[int, int] = defaultdict(int)
    for r in pair_rows:
        anchor_id = r["anchor_vcf_product_id"]
        overlap = r["shared_count"] / n_compounds_by_id[anchor_id] if n_compounds_by_id[anchor_id] else 0.0
        same_spine = spine_by_id.get(r["match_vcf_product_id"]) == spine_by_id.get(anchor_id)
        if overlap >= NEAR_DUP_OVERLAP_THRESHOLD and same_spine:
            r["suppressed_reason"] = NEAR_DUP_SUPPRESSED_REASON
            n_suppressed += 1
            anchors_with_suppression[anchor_id] += 1
        else:
            r["suppressed_reason"] = None

    # "Effective" top-1 per anchor for reporting purposes: the first row
    # NOT suppressed. With 0 suppressions this equals the raw top-1 for
    # every anchor; the machinery is exercised structurally either way.
    rows_by_anchor: dict[int, list] = defaultdict(list)
    for r in pair_rows:
        rows_by_anchor[r["anchor_vcf_product_id"]].append(r)
    effective_top1_scores = []
    for anchor_id, rows in rows_by_anchor.items():
        rows_sorted = sorted(rows, key=lambda r: r["rank"])
        first_unsuppressed = next((r for r in rows_sorted if not r["suppressed_reason"]), None)
        if first_unsuppressed:
            effective_top1_scores.append(first_unsuppressed["score"])
    median_top1_after_suppression = (
        statistics.median(effective_top1_scores) if effective_top1_scores else None
    )

    # Diagnostic recomputed fresh on every run (not a hardcoded historical
    # claim): how many anchors still have a top-1 match sharing >=85% of
    # the anchor's own compound set, now that Build 1's spine clustering
    # (apply_spine_clusters.py) has moved a first batch of genus/name-
    # variant near-duplicates onto a shared spine_id and out of this file's
    # candidate set entirely. Anything counted here, by construction, still
    # has a DIFFERENT spine_id from its anchor — either a genuine
    # containment artifact (LOBSTER/PRAWN) or a real near-duplicate the
    # clustering pass didn't reach yet (the 100 coverage-gap pairs pending
    # human review, or a cross-spirit/cross-wine residual).
    pre_suppression_top1 = {
        anchor_id: sorted(rows, key=lambda r: r["rank"])[0]
        for anchor_id, rows in rows_by_anchor.items()
        if rows
    }
    high_overlap_top1 = [
        (anchor_id, top) for anchor_id, top in pre_suppression_top1.items()
        if n_compounds_by_id.get(anchor_id) and top["shared_count"] / n_compounds_by_id[anchor_id] >= NEAR_DUP_OVERLAP_THRESHOLD
    ]
    raw_top1_scores = [top["score"] for top in pre_suppression_top1.values()]
    median_top1_raw = round(statistics.median(raw_top1_scores), 4) if raw_top1_scores else None
    sample_high_overlap = [
        f"{by_id[anchor_id]['raw_name']}/{top['match_raw_name']}"
        for anchor_id, top in sorted(high_overlap_top1, key=lambda t: -t[1]["score"])[:8]
    ]

    near_dup_report = {
        "overlap_threshold": NEAR_DUP_OVERLAP_THRESHOLD,
        "n_pairs_suppressed": n_suppressed,
        "n_anchors_affected": len(anchors_with_suppression),
        "suppressed_reason_value": NEAR_DUP_SUPPRESSED_REASON,
        "median_top1_score_after_suppression": round(median_top1_after_suppression, 4) if median_top1_after_suppression is not None else None,
        "median_top1_score_raw_pre_suppression": median_top1_raw,
        "n_anchors_with_high_overlap_top1": len(high_overlap_top1),
        "sample_high_overlap_top1_pairs": sample_high_overlap,
        "finding": (
            "n_pairs_suppressed=0, still. Condition 2 (same spine_id as "
            "anchor) can never be satisfied by anything in this file: the "
            "candidate-generation loop above already excludes same-"
            "spine_id pairs unconditionally ('if a[\"spine_id\"] == "
            "b[\"spine_id\"]: continue') before pairing scores are even "
            "computed, precisely so PEANUT (raw) never 'pairs' with "
            "PEANUT (roasted). Every pair that reaches this file, by "
            "construction, already has DIFFERENT spine_ids on the two "
            "sides — so a second condition that requires SAME spine_id "
            "is checking something that structurally cannot be true here. "
            "This is not a defect in the suppression code; Fix 3's second "
            "condition, AS SPECIFIED, remains a no-op against this corpus, "
            "for the same structural reason as before. What HAS changed: "
            f"n_anchors_with_high_overlap_top1 (>=85% of the anchor's own "
            f"compound set) is {len(high_overlap_top1)} as of this run — "
            "the real fix for this class of near-duplicate is spine-level "
            "clustering (Build 1, apply_spine_clusters.py), which removes "
            "a matched pair from candidate generation entirely rather than "
            "suppressing it after the fact, and has now been applied for "
            "the clusters spine_cluster_proposals.xlsx's human review "
            "approved. It is necessarily partial — 100 candidate pairs "
            "(meta.spine_clustering.n_coverage_gap_pairs_pending_review) "
            "had no binomial/genus data on either side to confirm or "
            "reject and were left for human review rather than merged — "
            "so this count is not expected to be zero. Sample of what's "
            "still here: " + ", ".join(sample_high_overlap) + ". median_"
            "top1_score_raw_pre_suppression reports the actual pre-"
            "suppression median honestly on every run rather than a frozen "
            "historical figure, since that figure moves as clustering "
            "coverage improves."
        ),
    }

    # --- Validation gate: coffee ---
    coffee_id = next((p["vcf_product_id"] for p in culinary if p["raw_name"] == COFFEE_RAW_NAME), None)
    coffee_report = {}
    if coffee_id is None:
        raise SystemExit(f"Validation target product {COFFEE_RAW_NAME!r} not found in the culinary corpus.")
    coffee_top = [r for r in pair_rows if r["anchor_vcf_product_id"] == coffee_id]
    coffee_top_names = {r["match_raw_name"]: r["rank"] for r in coffee_top}
    missing = []
    for label, raw_name in EXPECTED_COFFEE_MATCHES.items():
        rank = coffee_top_names.get(raw_name)
        coffee_report[label] = {"raw_name": raw_name, "rank_in_top_20": rank}
        if rank is None:
            missing.append(label)
    if missing:
        raise SystemExit(
            f"VALIDATION FAILED: coffee's top-{TOP_K_STORED} is missing expected matches: {missing}. "
            f"Coffee's actual top 10: {[r['match_raw_name'] for r in coffee_top[:10]]}. "
            f"Per spec — if coffee returns beverages instead, the IDF weighting isn't being applied. "
            f"Not writing output; investigate before re-running."
        )

    # --- Hub check --- (Fix 3: recomputed post-suppression — a suppressed
    # near-duplicate shouldn't inflate a product's hub-occupancy count; a
    # no-op today since n_suppressed==0, but correct if that ever changes)
    top10_occupants = Counter(
        r["match_vcf_product_id"] for r in pair_rows
        if r["rank"] <= TOP_K_HUB_CHECK and not r["suppressed_reason"]
    )
    n_culinary = len(culinary)
    hub_counts = top10_occupants.most_common(5)
    top_hub_id, top_hub_count = hub_counts[0]
    top_hub_frac = top_hub_count / n_culinary
    hub_report = [
        {"raw_name": by_id[pid]["raw_name"], "n_top10_appearances": cnt, "fraction": round(cnt / n_culinary, 4)}
        for pid, cnt in hub_counts
    ]

    with open(PAIRS_JSONL, "w") as f:
        for r in pair_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}

    # 2026-08-30: a VCF-only rebaseline's median_top1 score (0.2608) got
    # compared to a stray mixed-corpus number (0.2611, from a run that
    # included beef) with nothing in either artifact to stop it — James's
    # explicit instruction was to hold the two apart, but a bare float in
    # meta.json doesn't do that on its own the next time someone reads it
    # cold. corpus_scope is derived live from meta["profiles"] (written by
    # build_vcf_profiles.py just before this script runs), not hardcoded,
    # so it can't go stale the way a frozen label would.
    profiles_meta = meta.get("profiles", {})
    n_external_merged = profiles_meta.get("n_profiles_external_source_merged", 0)
    corpus_scope = "vcf_only" if not n_external_merged else "mixed_with_external_protein"

    meta["pairs"] = {
        "n_culinary_products_paired": n_culinary,
        "top_k_stored_per_product": TOP_K_STORED,
        "n_pair_rows": len(pair_rows),
        "corpus_scope": corpus_scope,
        "corpus_scope_note": (
            f"Derived live from meta['profiles']['n_profiles_external_source_merged'] "
            f"({n_external_merged}), not hardcoded. median_top1_score values in "
            f"near_duplicate_suppression below are only comparable to another "
            f"pairs.jsonl run with the SAME corpus_scope — a vcf_only run and a "
            f"mixed_with_external_protein run measure different, non-comparable "
            f"corpora even though the field name is identical."
        ),
        "coffee_validation": coffee_report,
        "hub_check_top5": hub_report,
        "hub_check_warn_threshold": HUB_WARN_THRESHOLD,
        "hub_check_exceeded_warn_threshold": top_hub_frac > HUB_WARN_THRESHOLD,
        "sample_comparison_hub_check": "roasted hazelnut, 36/182 (20%)",
        "near_duplicate_suppression": near_dup_report,
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {len(pair_rows)} pair rows ({n_culinary} products x top-{TOP_K_STORED}) to {PAIRS_JSONL}")
    print("Coffee validation:")
    for label, info in coffee_report.items():
        print(f"  {label}: rank {info['rank_in_top_20']}")
    print(f"Hub check top 5 (of top-{TOP_K_HUB_CHECK} lists, n={n_culinary}):")
    for h in hub_report:
        print(f"  {h['raw_name']}: {h['n_top10_appearances']} ({h['fraction']:.1%})")
    if top_hub_frac > HUB_WARN_THRESHOLD:
        print(f"WARNING: top hub occupant exceeds the {HUB_WARN_THRESHOLD:.0%} threshold — "
              f"metric may not be controlling for size.")
    print(f"\nNear-duplicate suppression (Fix 3): n_pairs_suppressed={n_suppressed}, "
          f"median_top1_score_after_suppression={near_dup_report['median_top1_score_after_suppression']}")


if __name__ == "__main__":
    main()
