"""
VCF Compound Layer — Step 9: resolution policy (single | expand | category).

Run from the repo root, AFTER build_vcf_spine.py:
    python pipeline/scripts/build_vcf_resolution_policy.py

Reads:  pipeline/artifacts/vcf/spine.jsonl   (Step 3 — members carry
        preparation/cure_state/state/form/cultivar/binomial already)
Writes: pipeline/artifacts/vcf/spine.jsonl   (same file, in place — fills in
        the `policy` field that build_vcf_spine.py deliberately left null,
        and adds `default_member`, `resolution_confidence`)
        pipeline/artifacts/vcf/meta.json    (adds a "resolution_policy" block)

Idempotent: policy/default_member/resolution_confidence are pure functions
of each entry's own member data, so re-running this after re-running
build_vcf_spine.py (which resets policy to null) reproduces the same
values every time — no state carried between runs.

--- Why member count alone doesn't decide the policy ---

VCF products are many-to-one against spine entries (nine pork, six apple,
four tomato), and per spec resolution "is a deterministic lookup, never a
model decision" — the same lookup must return the same policy every time,
so a reliability anchor can actually test it. But ">1 member" isn't itself
the deciding fact: RUM has four members (a generic entry plus three
"total volatiles" concentration bands) that are the same product measured
three ways, not three different rums a chef would choose between. PORK
also has more members, but cured and uncured pork are genuinely different
foods — averaging their profiles into one "range" would misrepresent both.
The policy has to track *what kind* of difference separates the members,
not how many there are.

--- The rule ---

Among a spine entry's CULINARY members (matching every earlier step's
corpus scope — reference members are analytical, not something a chef
picks between):

  n_culinary == 0   -> policy = null            (not applicable; Step 8's
                                                  "zero-culinary" bucket)
  n_culinary == 1   -> policy = "single"         (spec: no ambiguity)
  n_culinary >= 2   -> "category" if any of the following holds, else
                       "expand":
                         - `form` takes >=2 distinct values, counting None
                           as a value (whole/unprocessed vs juice vs paste
                           vs oil vs butter vs powder vs pulp vs extruded —
                           physically different foodstuffs, not degrees of
                           one food; unlike binomial below, None here is
                           itself meaningful — "no processing form applied"
                           — so a single member at form="juice" against
                           every other member at form=None is exactly the
                           same kind of split as two different non-null
                           forms, e.g. elderberry: whole vs juice)
                         - `cure_state` includes both "cured" and
                           "uncured" (pork's own VCF-native split)
                         - `binomial` takes >=2 distinct non-null values
                           (different scientific species under one common
                           name — e.g. American vs European cranberry,
                           Vaccinium macrocarpon vs V. oxycoccus; turmeric
                           vs wild turmeric, Curcuma longa vs C. aromatica)

`preparation` (raw/roasted/boiled/...) and `cultivar` do NOT trigger
category on their own. Preparation is exactly the continuum Step 8's form
diffs already model as "gained/lost," so "expand: compute per member,
report the range" is the right contract for it. Cultivar variation in this
corpus is almost always a named variety against a "generic"/unspecified
catch-all (apple's Elstar vs generic, pear's "OTHER TYPES," mushroom's
"OTHER VARIETIES") rather than a hard split a chef needs to be stopped and
asked about — and where cultivar variation IS structurally hard (apple),
`form` already fires (APPLE PROCESSED (juice)) so category is reached
anyway, for the field that's actually unambiguous.

This rule was checked against the three examples the spec itself names as
the motivating many-to-one cases — pork, apple, tomato — before being
trusted on the rest of the corpus: all three land on `category` (pork via
cure_state, apple and tomato via form), which is the result a chef's own
intuition would give. That agreement is evidence the rule is pointed at
the right signal, not proof it is complete — see Known blind spots below.

--- Known blind spots (flagged, not silently accepted) ---

`state` (fresh/processed/fermented/unprocessed/extruded) is deliberately
NOT a category trigger, because VCF's own naming is inconsistent about
whether a fermentation-type distinction lands in `state` or in
`preparation`: SHRIMPS (fermented) and RADISH (fermented) parse `fermented`
into `state`, but FERMENTED COCOA BEANS parses it into `preparation`
(prefix position vs suffix position in the raw string). Making `state`
trigger category would make cocoa_beans (fermented vs roasted — the same
kind of hard split as pork's cured vs uncured) `expand` while radish and
shrimps became `category` for the identical underlying distinction,
which is worse than treating all three the same and flagging the gap.

Separately, some real distinctions exist only as free text inside
`raw_name` that Step 2's parser doesn't capture as a structured field at
all — geographic origin (CALAMUS: Asian/European/North American), a
concentration-band label (RUM: Category I/II/III by total volatiles), a
plant part (BLACKBERRY: berry vs "leaves"), or a named multi-species blend
(RASPBERRY, BLACKBERRY and BOYSENBERRY). These fall through to `expand` by
this rule for lack of any structured signal to catch them, which may or
may not be right. `resolution_confidence` is set to "low" for exactly
this case (>=2 culinary members, classified `expand`, and NOT ONE of
preparation/cure_state/state/form/cultivar/binomial varies across them) so
these are locatable and reviewable rather than indistinguishable from the
ordinary raw/roasted case — see the low-confidence list this script
prints and records in meta.json. This mirrors Step 2's own precedent
("expect the tail to need hand correction") rather than claiming a
five-field parse resolves every real-world distinction.

--- default_member ---

For `expand`/`category` entries, `default_member` names which VCF product
a bare, unqualified lookup ("pork", "tomato") resolves to — required by
the spec's Balance-lens contract ("named default member only, never
average" / "named default, or decline to answer") and useful for the
Compound lens too as the anchor a range is reported relative to.

Deterministic tuple-sort over each entry's culinary members, cheapest/most
neutral member wins ties broken by lowest vcf_product_id so the result
never depends on JSONL row order:
  1. preparation == []          (no preparation applied beats any applied)
  2. cure_state is None         (unlabeled beats cured/uncured)
  3. form is None                (whole/base form beats a processed form)
  4. state is None               (unlabeled beats fresh/processed/fermented/...)
  5. cultivar rank: "generic" (0) beats untagged/None (1) beats a specific
                     named cultivar (2) — an explicit "generic" is the
                     strongest signal a chef means "no particular variety";
                     None is next-best since it doesn't assert a variety
                     even though the member may still BE one VCF didn't tag
  6. vcf_product_id              (final deterministic tiebreak)
This is a heuristic, not a semantic guarantee — apple's tuple-sort picks
whichever of the untagged "fresh" entries has the lowest id (a specific
cultivar can win over a more clearly generic one if the parser didn't tag
it), same caveat as the policy rule: deterministic and reviewable, not
asserted to be correct for the whole tail without a look.

For `single` entries, default_member is that one culinary member,
trivially. For 0-culinary entries, both fields are null.

--- What this does NOT do ---

Balance-lens code in this repo does not currently ingest VCF at all — per
spec, VCF is volatiles (aroma), not composition, and its only legitimate
Balance-lens contribution is strengthening the heat axis's existing
volatile-pungency side. This script only stores the policy value the spec
says Balance should eventually respect; it does not wire anything into
the heat axis or any other Balance code path. That's separate work, not
asked for here.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
SPINE_JSONL = OUT_DIR / "spine.jsonl"
META_JSON = OUT_DIR / "meta.json"


def classify(culinary_members: list[dict]) -> tuple[str, str]:
    """Returns (policy, confidence) for a spine entry's culinary members."""
    n = len(culinary_members)
    if n == 0:
        return None, None
    if n == 1:
        return "single", "high"

    # form: None is itself a meaningful value here ("no processing form
    # applied" — whole/fresh), not a "missing data" placeholder the way it
    # is for binomial. A single member with form="juice" against every
    # other member at form=None is exactly the same kind of split as two
    # members at "juice" vs "paste" — whole vs juice is still whole vs a
    # different physical foodstuff. Compare the FULL set (None included).
    forms_all = {m["form"] for m in culinary_members}
    cures = {m["cure_state"] for m in culinary_members if m["cure_state"]}
    binomials = {m["binomial"] for m in culinary_members if m["binomial"]}

    is_category = len(forms_all) >= 2 or {"cured", "uncured"} <= cures or len(binomials) >= 2
    if is_category:
        return "category", "high"

    # expand — check whether ANY structured field varies at all; if none
    # does, the members are only distinguished by free text this parser
    # doesn't capture (origin, concentration band, plant part, blend name).
    # (form/cure_state/binomial can only be *tied* at this point — a real
    # split in any of them would already have returned "category" above —
    # so only preparation/state/cultivar can still show variation here.)
    preps = {tuple(m["preparation"]) for m in culinary_members}
    states = {m["state"] for m in culinary_members}
    cultivars = {m["cultivar"] for m in culinary_members}
    any_structured_variation = len(preps) > 1 or len(states) > 1 or len(cultivars) > 1
    return "expand", ("high" if any_structured_variation else "low")


# Verified by hand against the full default_member table this rule
# produces (see the module docstring's "Known blind spots" section for the
# general caveat). Only ONE case was actually wrong on inspection:
# blackberry's mechanical default landed on the "(leaves)" member, not the
# fruit, because both the fresh-fruit and the leaves member have
# preparation=[] and every other tiebreak field tied too (leaves has no
# `state` tag while the fruit does, so "state is None" — meant to prefer
# an unlabeled/neutral member — backfired and favored the off-target plant
# part). Keyed by (spine_id, raw_name) rather than vcf_product_id, since
# vcf_product_id is assigned by row order in a re-pull and isn't a stable
# identity to hang an override on; raw_name is VCF's own stable key.
#
# raspberry added 2026-08-29 (James's "check everything" audit): same
# fruit-vs-"(leaves)" shape as blackberry — RASPBERRY (Rubus idaeus L.),
# RASPBERRY (leaves), and the RASPBERRY/BLACKBERRY/BOYSENBERRY blend all
# tie on every tiebreak field through cultivar (all preparation=[],
# cure_state/form/state/cultivar all None). It currently resolves to the
# fruit correctly, but only because vcf_product_id 443 < 444 < 446 — the
# same "isn't a stable identity" ordering accident that produced the
# blackberry bug, not yet triggered here only by luck of ID assignment.
# Locked in explicitly rather than left to keep winning by chance.
DEFAULT_MEMBER_OVERRIDES = {
    "culin:blackberry": "BLACKBERRY (fresh)",
    "culin:raspberry": "RASPBERRY (Rubus idaeus L.)",
}

# Build 1 (Sequenced Builds spec): policy overrides are a human review
# decision made against spine_cluster_proposals.xlsx, one cluster at a
# time (James, 2026-08-30 second pass: wine/whisky — no form/cure_state/
# binomial variation among the merged members, real distinction is style/
# region which lives only as free text in raw_name; plus 13 more
# plant-part and processing-state clusters — lovage/caraway/myrtle/
# pimento/blackcurrant/parsley/coconut/pear/mace, tea/olive/mate — where
# the members are different tissues or different processing states, not
# degrees of one food). `category` is the right policy for these — not
# because a mechanical field varies, but because a chef needs to be shown
# the members or asked which.
#
# This used to be a second hardcoded dict here, kept in sync with
# apply_spine_clusters.py's own bookkeeping by hand — exactly the
# "hardcoded narrative reasserts itself as true" failure this codebase has
# already hit twice (build_vcf_pairs.py's near-dup report, then
# apply_spine_clusters.py's own BINOMIAL_COVERAGE/CLUSTERING_PASS/
# N_COVERAGE_GAP_PAIRS constants). apply_spine_clusters.py already derives
# this mapping from the reviewed sheet and writes it to
# meta.json["spine_clustering"]["policy_overrides_applied_to"]; read it
# from there instead of re-declaring it, so a future family's overrides
# take effect by re-running the pipeline, not by editing two files in
# lockstep and hoping they don't drift.
def load_policy_overrides() -> dict[str, str]:
    if not META_JSON.exists():
        raise SystemExit(
            f"{META_JSON} not found — this script must run after "
            f"apply_spine_clusters.py, which writes the "
            f"spine_clustering.policy_overrides_applied_to block this "
            f"reads."
        )
    meta = json.loads(META_JSON.read_text())
    spine_clustering = meta.get("spine_clustering")
    if spine_clustering is None:
        raise SystemExit(
            f"{META_JSON} has no 'spine_clustering' block — run "
            f"apply_spine_clusters.py before this script (see this "
            f"script's own module docstring ordering)."
        )
    return dict(spine_clustering.get("policy_overrides_applied_to", {}))


def default_member_id(spine_id: str, culinary_members: list[dict]) -> str:
    override_raw_name = DEFAULT_MEMBER_OVERRIDES.get(spine_id)
    if override_raw_name is not None:
        hit = next((m for m in culinary_members if m["raw_name"] == override_raw_name), None)
        if hit is None:
            # The override was written against a specific raw_name that no
            # longer exists for this entry — a re-pull changed something.
            # Fail loud rather than silently falling back to the mechanical
            # rule, which is exactly the failure mode this override exists
            # to avoid.
            raise SystemExit(
                f"DEFAULT_MEMBER_OVERRIDES[{spine_id!r}] names raw_name "
                f"{override_raw_name!r}, which is not among this entry's "
                f"current culinary members — re-verify the override "
                f"against the new data (see the module docstring)."
            )
        return hit["vcf_product_id"]

    def key(m):
        # cultivar: an explicit "generic" beats an untagged member (which
        # may still be one specific named variety VCF just didn't tag —
        # e.g. apple's "Elstar" and "Malus species" members both have
        # cultivar=None, same as "generic" would if the parser called it
        # that) which beats a specifically named cultivar/variety.
        cultivar_rank = 0 if m["cultivar"] == "generic" else (1 if m["cultivar"] is None else 2)
        return (
            0 if m["preparation"] == [] else 1,
            # Secondary signal when every candidate carries SOME
            # preparation (e.g. chestnuts: only boiled/raw/roasted exist,
            # no bare member) — prefer 'raw' over falling through to
            # vcf_product_id order, which carries no semantic meaning
            # (it's assignment order from the raw CSV pull, not a ranking).
            0 if "raw" in m["preparation"] else 1,
            0 if m["cure_state"] is None else 1,
            0 if m["form"] is None else 1,
            0 if m["state"] is None else 1,
            cultivar_rank,
            m["vcf_product_id"],
        )
    return min(culinary_members, key=key)["vcf_product_id"]


def main():
    if not SPINE_JSONL.exists():
        raise SystemExit(f"{SPINE_JSONL} not found — run build_vcf_spine.py first.")

    entries = [json.loads(l) for l in SPINE_JSONL.read_text().splitlines() if l.strip()]
    policy_overrides = load_policy_overrides()

    policy_counts: Counter = Counter()
    low_confidence: list[dict] = []
    named_examples = {}
    policy_overrides_applied = []
    unused_overrides = set(policy_overrides)

    for e in entries:
        culin = [m for m in e["members"] if m["class"] == "culinary"]
        policy, confidence = classify(culin)
        if e["spine_id"] in policy_overrides:
            unused_overrides.discard(e["spine_id"])
            override_policy = policy_overrides[e["spine_id"]]
            policy_overrides_applied.append(
                {
                    "spine_id": e["spine_id"],
                    "rule_output": f"{policy}/{confidence}",
                    "override": override_policy,
                }
            )
            policy, confidence = override_policy, "override"
        e["policy"] = policy
        e["resolution_confidence"] = confidence
        e["default_member"] = default_member_id(e["spine_id"], culin) if culin else None
        policy_counts[policy] += 1
        if policy == "expand" and confidence == "low":
            low_confidence.append(
                {
                    "spine_id": e["spine_id"],
                    "members": [m["raw_name"] for m in culin],
                }
            )
        if e["spine_id"] in ("culin:pork", "culin:apple", "culin:tomato"):
            named_examples[e["spine_id"]] = {
                "policy": policy,
                "default_member_raw_name": next(
                    m["raw_name"] for m in culin if m["vcf_product_id"] == e["default_member"]
                ),
            }

    if unused_overrides:
        raise SystemExit(
            f"policy_overrides_applied_to names spine_id(s) "
            f"{sorted(unused_overrides)} that don't match any current "
            f"spine entry — apply_spine_clusters.py's canonical-name pick "
            f"may have changed, or spine.jsonl was rebuilt without "
            f"re-running apply_spine_clusters.py. Silently dropping an "
            f"override is the same failure mode James flagged for "
            f"coverage-gap pairs: don't let a mismatch here vanish "
            f"unreported."
        )

    with open(SPINE_JSONL, "w") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["resolution_policy"] = {
        "policy_counts": dict(policy_counts),
        "rule": (
            "category if form varies (>=2 distinct non-null), or cure_state "
            "includes both cured and uncured, or binomial varies (>=2 "
            "distinct non-null); else expand if >=2 culinary members; else "
            "single (1) or null (0, not applicable)."
        ),
        "spec_named_examples": named_examples,
        "n_low_confidence_expand": len(low_confidence),
        "low_confidence_expand_entries": low_confidence,
        "low_confidence_note": (
            "These spine entries have >=2 culinary members classified "
            "'expand' where NOT ONE of preparation/cure_state/state/form/"
            "cultivar/binomial varies across the members — the only "
            "difference is free text in raw_name (geographic origin, a lab "
            "concentration band, a plant part, a named multi-species blend) "
            "that Step 2's parser doesn't capture as a structured field. "
            "Flagged rather than silently trusted; a human call, same as "
            "Step 2's own reviewable-tail precedent."
        ),
        "balance_lens_note": (
            "Policy values are stored per spec so a future Balance-lens "
            "VCF integration (heat axis, volatile-pungency side only) can "
            "consult them. No Balance-lens code path reads them yet — that "
            "wiring is separate work, not part of this build."
        ),
        "policy_overrides_applied": policy_overrides_applied,
        "policy_overrides_note": (
            "A human override of this rule's mechanical output — see "
            "POLICY_OVERRIDES in this script for why. 'rule_output' is "
            "what classify() computed before the override; 'override' is "
            "what was actually written. confidence='override' distinguishes "
            "this from the rule's own high/low so a reader never mistakes "
            "a deliberate call for the mechanical result."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Resolution policy assigned across {len(entries)} spine entries:")
    for policy, count in sorted(policy_counts.items(), key=lambda kv: str(kv[0])):
        print(f"  {policy!s:<10} {count}")
    print(f"\nSpec-named examples (pork/apple/tomato):")
    for spine_id, info in named_examples.items():
        print(f"  {spine_id:<14} policy={info['policy']:<10} default={info['default_member_raw_name']}")
    print(f"\nLow-confidence 'expand' entries (no structured field distinguishes members): "
          f"{len(low_confidence)}")
    for lc in low_confidence:
        print(f"  {lc['spine_id']:<20} {lc['members']}")
    if policy_overrides_applied:
        print(f"\nPolicy overrides applied: {len(policy_overrides_applied)}")
        for o in policy_overrides_applied:
            print(f"  {o['spine_id']:<20} rule={o['rule_output']:<16} -> override={o['override']}")


if __name__ == "__main__":
    main()
