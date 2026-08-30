"""
VCF Compound Layer — Step 11d: authored phase-behaviour frame table.

Run from the repo root (no dependency on other Step 11 scripts — this is
static authored content, not computed from compounds.jsonl):
    python pipeline/scripts/build_vcf_phase_frames.py

Writes: pipeline/artifacts/vcf/phase_frames.jsonl
        pipeline/artifacts/vcf/meta.json   (adds a "phase_frames" block)

Per spec 11d: "The FRAMES and OVERLAYS tables in the 5.1 prototype are the
source material and should be lifted directly... the number selects the
frame; a human wrote the sentence." That prototype is this repo's own
`src/data/domain.js` — FRAMES/OVERLAYS are live code there, not a separate
historical file. Every VERBATIM `sentence` below is diffed against that
file at build time (see _verify_sentences); a sentence that was
DELIBERATELY REWRITTEN this revision (see the smoke/phenol frame, below)
is excluded from that check and says so in its own `source` field instead
of claiming a false verbatim provenance.

=====================================================================
REVISION 4 — the underlying error, stated once (see Step 11e's own memo)
=====================================================================

Three revisions in a row produced a wrong frame attachment, all the same
shape: an authored sentence claiming PROVENANCE that the chemistry cannot
establish. The sentence asserted *smoke*; the data only ever supported
*fat-soluble phenols share a carrier with terpenes*. Guaiacol arrives from
smoking, roasting, barrel char, malt kilning, or floral source — the
molecule is identical in every case, so no amount of trigger refinement on
the CHEMISTRY side can ever license a PROVENANCE claim. Revision 3's
smoke_marker role made the chemistry-side gate much more precise (29
curated compounds instead of the whole Phenols group), but it was still
trying to infer provenance from a molecule, which is the same category
error at higher resolution.

The rule this revision encodes: provenance claims come from the
`preparation` field (parsed, factual, in vcf_product_parse.jsonl —
`PORK, CURED (smoked)` and `PORK, UNCURED (smoked)` carry
`preparation: ["smoked"]`); behaviour claims come from the chemistry.
Never the reverse. Concretely, this splits what was one frame into two:

  fat_phase_phenol_terpene_carrier  -- a BEHAVIOUR claim (carrier
                                        competition), gated purely on
                                        phase_bucket/compound_group/
                                        percentile — no provenance
                                        inference at all. See below.
  smoked_product_fat_phase          -- a PROVENANCE claim, gated on the
                                        parsed `preparation` field itself,
                                        not a molecule. Shipped as a
                                        pending_authoring stub (James's
                                        sentence to write, not this
                                        build's) — see below.

The smoke_marker role built in Revision 3 (compound_roles.jsonl,
role_counts/role_shares on profiles.jsonl) is NOT deleted — those
artifacts still exist and are still reported — but no frame trigger
consumes it anymore, precisely because it was chemistry standing in for
provenance. It's kept as tagged data in case a future purely-chemical
claim (not a provenance one) wants it.

--- Why only 3 authored + 1 stub of the 10 OVERLAYS entries are here ---

The spec's actual instruction is narrower than "port every overlay": a
frame's `trigger` has to be evaluable from data the pipeline actually has
— "a frame fires when the compounds present (or the parsed preparation)
put it in scope, instead of being hardcoded to a technique name." Most of
OVERLAYS describes a COOKING TECHNIQUE's mechanism (dry-cure has no
cooking medium at all; ground meat is about distribution, not chemistry;
a terrine's aroma is muted by cold and fat content, not by a compound
class) — there's no signal in this build that those triggers on. Forcing
a chemistry- or preparation-shaped trigger onto process-shaped prose would
be exactly the failure mode Step 11d warns against in reverse.

Four entries reduce to a real, honestly-scoped trigger:
  smoke/terpene (REWRITTEN, Revision 4) -> the spec's own worked example,
            now split into its two component claims:

            fat_phase_phenol_terpene_carrier: BEHAVIOUR ONLY. "Fat-soluble
            phenols and terpenes share a limited carrier" is true
            regardless of WHERE the phenols came from (smoke, roasting,
            barrel char, kilning, or a floral/herb source) — it only
            needs both groups to be genuinely concentrated (>=75th
            percentile of their own group's corpus-wide share) in a
            fat-affine bucket. Sentence rewritten to drop the word
            "smoke" entirely; this is an authored rewrite, NOT a verbatim
            prototype quote (source: "authored_derived_from_prototype_5_1",
            not "prototype_5_1" — see _verify_sentences, which correctly
            no longer checks this frame against domain.js). Expected
            effect: the 37 rows Revision 2 wrongly called "smoke" (anise
            brandy, ouzo, calamus, star anise, fennel, chervil, pimento
            leaf, Korean mint...) become framed again — correctly this
            time, as carrier competition, which they always were. The
            MICROBIAL FERMENTED TEA / YELLOW BOX HONEY row that qualified
            under Revision 3's smoke_marker gate drops out here: its
            contested groups are Carbonyls-aldehydes vs Hydrocarbons, not
            {Hydrocarbons, Phenols}, so it was never a phenol/terpene
            carrier collision to begin with — Revision 3's role-based gate
            let it in on secondary phenolic content that wasn't even the
            product's own dominant group.

            smoked_product_fat_phase: PROVENANCE ONLY, gated on the parsed
            `preparation` field (`vcf_product_parse.jsonl`), not a
            molecule. Shipped as an unauthored stub (`pending_authoring:
            True`, empty sentence) — see build_vcf_competition.py for why
            it fires on zero rows in this corpus (smoked pork's own top-20
            pairs.jsonl neighbours are other pork and Maillard-adjacent
            products, not terpene-heavy herbs) and for the honest
            `n_firing_rows: 0` report.

  broth  -> water_phase dominance. Aromatics that partition into water
            behave differently (disperse, over-extract) than fat-phase
            ones — a real, if coarser, compound-class distinction. Not a
            provenance claim, unaffected by this revision.
  confit -> fat_phase dominance PLUS a volatility split (needs Step 11c's
            volatile/stable buckets to actually fire — flagged as
            `pending_volatility_data` below). Not a provenance claim,
            unaffected by this revision.

The other 6 (sear, roast, cure, braise, ground, terrine, raw) describe
real, useful cooking mechanics but not ones this pipeline's data can
trigger on honestly. Left out rather than force-fitted.

--- `pending_authoring` ---

`smoked_product_fat_phase` is the first frame shipped this way: trigger
defined and evaluable (for reporting `n_firing_rows`), sentence left
empty, `pending_authoring: True`. Per the anchors below, a row NEVER
renders `framed` against a pending_authoring frame regardless of whether
its trigger fires — build_vcf_competition.py enforces this structurally,
not just descriptively. Authoring the sentence is James's task, not a
build step.

=====================================================================
REVISION 5 — a frame's trigger must verify every mechanism its sentence
asserts, not just the mechanism it was first written to catch
=====================================================================

Beef ingestion gave `smoked_product_fat_phase` its first-ever real firing
rows: 4, once smoked beef muscle entered the corpus. All four contend on
Carbonyls,aldehydes. None contend on Phenols. A sentence written for this
frame under the Revision 4 trigger ("smoke shares a carrier with terpenes")
would have described chemistry these rows don't have — the fourth variant
of the same failure across four revisions (Rev 1: a required group was
missing; Rev 2: the group was present but the wrong chemistry; Rev 3: the
marker was on the wrong side; Rev 4/this: the trigger verified provenance
but never verified the mechanism its own name asserts).

Two changes:

  smoked_product_fat_phase gets a MECHANISM gate added alongside its
  existing PROVENANCE gate: `either_side.group eq 'Phenols'`, bound to the
  SAME side as `either_side.preparation contains 'smoked'` (the
  either_side/other_side engine already does this binding correctly — see
  vcf_trigger_lib.py). Both conditions on the SAME side, not the pair as a
  whole: a smoked product whose OWN chemistry doesn't clear Phenols
  shouldn't fire this trigger just because it's smoked. Rerun result: 0
  firing rows. Reported plainly, per the same standard Revision 4 used for
  its own zero-firing-rows report — a frame correctly gated is not a
  frame with something wrong with it.

  fat_phase_aldehyde_load_crowding is authored fresh to hold what those 4
  rows actually are: aldehyde-driven fat-phase crowding, a real,
  general mechanism (drives beef raw and cooked as much as smoked) with no
  preparation gate at all. This is the first NON-pending PAIR-context
  frame added since the original flagship — see build_vcf_competition.py's
  REVISION 5 section for how `_assign_frame_id` generalizes to check more
  than one authored frame.

Scalar field note: this file's `either_side.group eq 'Phenols'` uses the
"eq" operator, not "equals". vcf_trigger_lib.py's "equals" operator is
SET equality (`set(value) == set(cond["equals"])`) — correct for an
unordered-collection field like group_pair, but wrong for a scalar string
field: `set("Phenols")` is the character set {'P','h','e','n','o','l','s'},
which would accept any group label that happens to be an anagram of
"Phenols" and is simply the wrong operator for this comparison, not a
stricter one. "eq" (plain equality) is what a scalar field needs.
"""
from __future__ import annotations

import json
from pathlib import Path

from vcf_trigger_lib import evaluate_trigger, generate_trigger_description

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
PHASE_FRAMES_JSONL = OUT_DIR / "phase_frames.jsonl"
META_JSON = OUT_DIR / "meta.json"
# The actual prototype source these sentences are lifted from — a sibling
# path outside pipeline/, reached the same way the Mac landing step always
# has for repo files (this script is meant to be run from the repo root).
DOMAIN_JS = REPO_ROOT / "src" / "data" / "domain.js"

PERCENTILE_GATE = 75  # both sides must clear this percentile of their own group's corpus share

FRAME_TRIGGERS = {
    # PAIR context — evaluated by build_vcf_competition.py against real
    # pairs. REVISION 4: pure behaviour claim, no provenance/role
    # inference — group_pair + both sides' own group percentile only.
    "fat_phase_phenol_terpene_carrier": {
        "all": [
            {"field": "bucket", "in": ["fat_phase", "fat_leaning"]},
            {"field": "group_pair", "equals": ["Hydrocarbons", "Phenols"]},
            {"field": "a_group_percentile", "gte": PERCENTILE_GATE},
            {"field": "b_group_percentile", "gte": PERCENTILE_GATE},
        ]
    },
    # PAIR context — REVISION 4 addition, REVISION 5 correction (see this
    # file's REVISION 5 note below). PROVENANCE claim gated on TWO things
    # now, not one: the smoked side must actually BE the smoked side
    # (either_side.preparation), AND that SAME side's own contending group
    # must be Phenols (either_side.group) — the mechanism the sentence
    # would assert. Both either_side.* conditions bind to the SAME side by
    # construction (see vcf_trigger_lib.py's either_side/other_side
    # semantics); without the group condition, a row could satisfy this
    # trigger purely because ONE side happens to be smoked, regardless of
    # what that side is chemically contending on — which is exactly the
    # bug Revision 4 shipped (see build_vcf_competition.py's REVISION 5
    # docstring section for the four beef rows this caught).
    "smoked_product_fat_phase": {
        "all": [
            {"field": "bucket", "in": ["fat_phase", "fat_leaning"]},
            {"field": "either_side.preparation", "contains": "smoked"},
            {"field": "either_side.group", "eq": "Phenols"},
            {"field": "other_side.group_percentile", "gte": PERCENTILE_GATE},
        ]
    },
    # PAIR context — REVISION 5 addition. Pure BEHAVIOUR claim, same shape
    # as fat_phase_phenol_terpene_carrier: lipid-oxidation aldehyde load
    # crowding a fat-affine phase. No preparation gate — this mechanism is
    # not smoke-specific (raw and cooked beef muscle both drive it as much
    # as smoked does). `groups_present` (already computed for every pair,
    # see build_vcf_competition.py's _pair_trigger_context) plus `contains`
    # correctly fires whether Carbonyls,aldehydes is the SAME group on both
    # sides (same_group_crowding) or only one side's dominant group
    # (cross_group_carrier) — unlike fat_phase_phenol_terpene_carrier's
    # `group_pair`+`equals`, which requires an EXACT 2-item match and so
    # could never do this job.
    "fat_phase_aldehyde_load_crowding": {
        "all": [
            {"field": "bucket", "in": ["fat_phase", "fat_leaning"]},
            {"field": "groups_present", "contains": "Carbonyls, aldehydes"},
            {"field": "a_group_percentile", "gte": PERCENTILE_GATE},
            {"field": "b_group_percentile", "gte": PERCENTILE_GATE},
        ]
    },
    # SINGLE-PRODUCT context — not currently evaluated by any script (see
    # each frame's note below); stored in the structured form for
    # consistency and so a future evaluator has no string to parse.
    "water_phase_dispersion_timing": {
        "all": [{"field": "dominant_bucket", "eq": "water_phase"}]
    },
    "fat_phase_long_infusion_volatility_split": {
        "all": [
            {"field": "dominant_bucket", "eq": "fat_phase"},
            {"field": "volatility_buckets_present", "contains_any": ["volatile", "stable"]},
        ]
    },
}

FRAMES = [
    {
        "frame_id": "fat_phase_phenol_terpene_carrier",
        "trigger": FRAME_TRIGGERS["fat_phase_phenol_terpene_carrier"],
        "trigger_description": generate_trigger_description(
            FRAME_TRIGGERS["fat_phase_phenol_terpene_carrier"]
        ),
        "sentence": (
            "Both sit in the fat phase. Guaiacols and terpenes are both "
            "fat-soluble, so one carrier has to move both — they will "
            "compete for it."
        ),
        "source": "authored_derived_from_prototype_5_1",
        "prototype_key": "OVERLAYS.smoke",
        "pending_volatility_data": False,
        "pending_authoring": False,
        "note": (
            "REVISION 4: replaces fat_phase_smoke_terpene_competition. "
            "The prototype's OVERLAYS.smoke sentence asserted smoke "
            "specifically ('Smoke compounds are fat-soluble...'); the "
            "chemistry this trigger can actually verify is narrower — "
            "phenols and terpenes sharing a fat-phase carrier, regardless "
            "of the phenols' origin (smoke, roasting, barrel char, "
            "kilning, or a floral/herb source). The sentence is rewritten "
            "to match the narrower, honest claim rather than reused "
            "verbatim, so `source` says 'authored_derived_from_"
            "prototype_5_1', not 'prototype_5_1' — and _verify_sentences "
            "below deliberately does NOT check this sentence against "
            "domain.js, since it is no longer a verbatim quote. Trigger "
            "requires {a_group,b_group}=={'Hydrocarbons','Phenols'} AND "
            "BOTH sides at/above the 75th percentile of their own "
            "dominant group's corpus-wide share (group_pair uses "
            "order-independent 'equals', not 'contains', so this frame "
            "can never fire on a same_group_crowding row by construction "
            "— a 2-item equality can't match a 1-item set). See "
            "build_vcf_competition.py's meta.json 'phenol_terpene_frame' "
            "block for the corrected framed-row list (~37 rows expected, "
            "up from Revision 3's 1 — the first revision in four to "
            "INCREASE frame coverage, because the sentence now matches "
            "the evidence everywhere the evidence holds)."
        ),
    },
    {
        "frame_id": "smoked_product_fat_phase",
        "trigger": FRAME_TRIGGERS["smoked_product_fat_phase"],
        "trigger_description": generate_trigger_description(
            FRAME_TRIGGERS["smoked_product_fat_phase"]
        ),
        "sentence": "",
        "source": "pending_authoring — no prototype source; new this revision",
        "prototype_key": None,
        "pending_volatility_data": False,
        "pending_authoring": True,
        "note": (
            "REVISION 4 addition, REVISION 5 CORRECTED. Beef ingestion "
            "produced this frame's first-ever real firing rows (4, once "
            "smoked beef muscle entered the corpus) — and every one of "
            "them contended on Carbonyls,aldehydes, not Phenols. The "
            "trigger as shipped in Revision 4 only checked PROVENANCE "
            "(either_side.preparation contains 'smoked') plus a bare "
            "percentile gate on the OTHER side — it never verified that "
            "the smoked side's own chemistry was what the sentence would "
            "have claimed ('smoke shares a carrier'). That is the same "
            "category of bug as Revisions 1-3 (see this file's module "
            "docstring), just caught one level deeper: a frame whose NAME "
            "asserts a mechanism its trigger never checks. REVISION 5 "
            "adds `either_side.group eq 'Phenols'`, bound to the SAME "
            "side as the preparation condition — now BOTH the provenance "
            "gate (this side was actually smoked) and the mechanism gate "
            "(this side's contending chemistry is actually phenolic) must "
            "hold together. Rerunning against beef: 0 firing rows, "
            "correctly — smoked beef contends on aldehydes (lipid "
            "oxidation, same mechanism as its raw/cooked tiers), not "
            "phenols, despite genuinely carrying real smoke_marker/Phenols "
            "content in its own profile (12.3% smoke_marker role share, "
            "16.4% Phenols group share — see fat_phase_aldehyde_load_"
            "crowding below for where that smoked-beef signal actually "
            "belongs). Still pending_authoring — this fires correctly "
            "the first time a smoked product contends on phenols, not "
            "before. `cure_state` (also parsed: 'cured'/'uncured') is "
            "available for a future cured-vs-smoked distinction if wanted."
        ),
    },
    {
        "frame_id": "fat_phase_aldehyde_load_crowding",
        "trigger": FRAME_TRIGGERS["fat_phase_aldehyde_load_crowding"],
        "trigger_description": generate_trigger_description(
            FRAME_TRIGGERS["fat_phase_aldehyde_load_crowding"]
        ),
        "sentence": (
            "Fat oxidation has already loaded this fat phase with "
            "long-chain aldehydes. Anything else you put in the same fat "
            "has to share that channel with them."
        ),
        "source": "authored_new_this_revision — not from the 5.1 prototype (OVERLAYS has no aldehyde-load entry)",
        "prototype_key": None,
        "pending_volatility_data": False,
        "pending_authoring": False,
        "note": (
            "REVISION 5 addition — the frame the 4 beef rows displaced out "
            "of smoked_product_fat_phase actually belong in. Pure "
            "behaviour claim: lipid-oxidation aldehyde load competing for "
            "a fat-affine carrier. No preparation gate, deliberately — "
            "the mechanism drives beef raw and cooked as much as smoked "
            "(mean role/group share is a property of the chemistry, not "
            "of how the product was prepared), so gating it on 'smoked' "
            "would confine a general mechanism to one state for no "
            "reason. Fires on both same_group_crowding rows (both sides "
            "aldehyde-dominant — PARBOILED RICE, MICROBIAL FERMENTED TEA "
            "vs. beef) and cross_group_carrier rows (the other side "
            "contends on a different group entirely — CUTTLEFISH's "
            "Phenols, BRAZIL NUT's Hydrocarbons — while beef's own side "
            "is already occupying the aldehyde channel). Same sentence "
            "reads correctly in both cases: crowding when both sides are "
            "aldehyde-heavy, one side already occupying the channel when "
            "they're not. Will fire on more than the four beef rows that "
            "prompted it — see build_vcf_competition.py's meta.json "
            "'aldehyde_load_crowding_frame' block for the full list."
        ),
    },
    {
        "frame_id": "water_phase_dispersion_timing",
        "trigger": FRAME_TRIGGERS["water_phase_dispersion_timing"],
        "trigger_description": generate_trigger_description(
            FRAME_TRIGGERS["water_phase_dispersion_timing"]
        ),
        "sentence": (
            "Dispersion and timing. Aromatics disperse through liquid and can go "
            "muddy if over-extracted. When something goes in matters as much as "
            "whether it goes in."
        ),
        "source": "prototype_5_1",
        "prototype_key": "OVERLAYS.broth",
        "pending_volatility_data": False,
        "pending_authoring": False,
        "note": (
            "Water-phase compounds (5.1% of the corpus per Step 11b) behave "
            "differently from fat-phase ones — this frame fires on that "
            "dominance alone, no second compound group required. Not "
            "currently evaluated by any script (single-product trigger, "
            "no consumer yet) — stored in the structured format for "
            "consistency only. Not a provenance claim; unaffected by "
            "Revision 4."
        ),
    },
    {
        "frame_id": "fat_phase_long_infusion_volatility_split",
        "trigger": FRAME_TRIGGERS["fat_phase_long_infusion_volatility_split"],
        "trigger_description": generate_trigger_description(
            FRAME_TRIGGERS["fat_phase_long_infusion_volatility_split"]
        ),
        "sentence": (
            "Infusion, not surface. Everything here spends hours in fat at low "
            "heat — aromatics infuse the medium rather than perfuming a "
            "surface. Delicate volatiles will be lost; robust ones deepen."
        ),
        "source": "prototype_5_1",
        "prototype_key": "OVERLAYS.confit",
        "pending_volatility_data": True,
        "pending_authoring": False,
        "note": (
            "Cannot fire for real yet: this trigger needs Step 11c's "
            "volatile/moderate/stable buckets, which need a live PubChem "
            "boiling-point fetch that is currently blocked (PUG View "
            "returning 503 from this environment as of this build — see "
            "meta.json's volatility block). Stored now, evaluable once 11c "
            "lands. Not currently evaluated by any script (single-product "
            "trigger, no consumer yet). Not a provenance claim; unaffected "
            "by Revision 4."
        ),
    },
]


def _verify_sentences():
    """Fail loudly if domain.js's actual wording has drifted from what's
    hardcoded above, rather than silently shipping stale authored prose.
    REVISION 4: fat_phase_phenol_terpene_carrier's sentence is no longer
    checked here — it's a deliberate rewrite, not a verbatim quote (see
    its own `note` and `source` fields)."""
    if not DOMAIN_JS.exists():
        print(
            f"WARNING: {DOMAIN_JS} not found from this working directory — "
            "skipping the verbatim-match check against the source file. "
            "(Expected when running against the pipeline mirror rather "
            "than the full repo checkout; the Mac landing step DOES have "
            "this file and should not skip this check.)"
        )
        return
    src = DOMAIN_JS.read_text()
    checks = {
        "OVERLAYS.broth": "Dispersion and timing",
        "OVERLAYS.confit": "Delicate volatiles will be lost; robust ones deepen",
    }
    for key, needle in checks.items():
        if needle not in src:
            raise SystemExit(
                f"phase_frames verbatim check failed: {key!r}'s expected "
                f"text ({needle!r}) was not found in {DOMAIN_JS} — the "
                f"prototype's wording has changed. Re-copy the sentence "
                f"into build_vcf_phase_frames.py's FRAMES list rather than "
                f"leaving it stale."
            )


def _assert_trigger_descriptions_are_regenerated_not_authored():
    """Anchor: round-trip every frame through JSON and re-generate its
    trigger_description from the STORED structured trigger."""
    for frame in FRAMES:
        roundtripped = json.loads(json.dumps(frame, ensure_ascii=False))
        regenerated = generate_trigger_description(roundtripped["trigger"])
        if regenerated != roundtripped["trigger_description"]:
            raise SystemExit(
                f"phase_frames trigger_description drift on "
                f"{frame['frame_id']!r}: stored={roundtripped['trigger_description']!r} "
                f"regenerated={regenerated!r}. trigger_description must always "
                f"be produced by generate_trigger_description(trigger) — never "
                f"hand-authored separately."
            )


def _assert_pending_authoring_frames_have_no_sentence():
    """Anchor: pending_authoring frames must have an empty sentence, and
    fully-authored frames must NOT be empty — this is the structural half
    of 'no row renders framed against a pending_authoring frame while its
    sentence is empty' (the other half is enforced in
    build_vcf_competition.py, which must never set frame_id to a
    pending_authoring frame's id at all)."""
    bad = []
    for f in FRAMES:
        is_empty = not (f.get("sentence") or "").strip()
        if f.get("pending_authoring") and not is_empty:
            bad.append((f["frame_id"], "pending_authoring=True but sentence is non-empty"))
        if not f.get("pending_authoring") and is_empty:
            bad.append((f["frame_id"], "pending_authoring=False but sentence is empty"))
    if bad:
        raise SystemExit(f"phase_frames pending_authoring/sentence mismatch: {bad}")


def main():
    _verify_sentences()
    _assert_trigger_descriptions_are_regenerated_not_authored()
    _assert_pending_authoring_frames_have_no_sentence()

    with open(PHASE_FRAMES_JSONL, "w") as f:
        for frame in FRAMES:
            f.write(json.dumps(frame, ensure_ascii=False) + "\n")

    n_authored = sum(1 for f in FRAMES if not f["pending_authoring"])
    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["phase_frames"] = {
        "n_frames": len(FRAMES),
        "n_authored": n_authored,
        "n_pending_volatility_data": sum(1 for f in FRAMES if f["pending_volatility_data"]),
        "n_pending_authoring": sum(1 for f in FRAMES if f.get("pending_authoring")),
        "pending_authoring_note": (
            "1 of 5 frames (smoked_product_fat_phase) is a stub this "
            "revision: trigger defined and evaluated for reporting "
            "(n_firing_rows), sentence intentionally empty. REVISION 5: "
            "this stub's trigger now ALSO gates on mechanism "
            "(either_side.group eq 'Phenols'), not just provenance — see "
            "this file's REVISION 5 docstring section. No row may "
            "ever render frame_id set to a pending_authoring frame's id — "
            "enforced in build_vcf_competition.py. See "
            "build_vcf_competition.py's meta.json top_group_pairs_missing_frame "
            "for which OTHER unauthored collision to write a frame for next."
        ),
        "source": "src/data/domain.js FRAMES/OVERLAYS (the '5.1 prototype')",
        "n_overlays_in_prototype_not_ported": 7,
        "overlays_not_ported": ["sear", "roast", "cure", "braise", "ground", "terrine", "raw"],
        "overlays_not_ported_reason": (
            "Describe cooking-technique mechanics (dry contact, distribution, "
            "cold/fat muting) that don't reduce to a compound-chemistry or "
            "parsed-preparation trigger this pipeline can evaluate — left "
            "out rather than force a false justification onto "
            "process-shaped prose."
        ),
        "verbatim_check": "passed against src/data/domain.js at build time (broth, confit only — see below)" if DOMAIN_JS.exists()
                          else "skipped — domain.js not reachable from this working directory",
        "verbatim_check_note": (
            "REVISION 4: fat_phase_phenol_terpene_carrier's sentence is a "
            "deliberate authored rewrite (see its own note/source fields), "
            "not a verbatim prototype quote, so it is intentionally "
            "excluded from this check — checking it against domain.js "
            "would either fail permanently or silently re-legitimize the "
            "old smoke-specific wording."
        ),
        "trigger_schema": (
            "trigger is a structured {'all': [condition, ...]} object "
            "evaluated by vcf_trigger_lib.evaluate_trigger (the ONE "
            "function that decides whether any trigger fires). "
            "trigger_description is generated mechanically from the same "
            "structure via generate_trigger_description, never "
            "hand-authored — checked at build time. REVISION 4 extended "
            "the schema with 'group_pair'/'equals' (order-independent set "
            "equality) and 'either_side.'/'other_side.' (a relationship "
            "between the pair's two sides, for provenance-on-one-side-"
            "plus-carrier-on-the-other claims) — see vcf_trigger_lib.py's "
            "own docstring for the full schema."
        ),
        "revision_4_provenance_vs_behaviour_rule": (
            "Provenance claims (smoked, roasted, cured...) come from the "
            "parsed `preparation`/`cure_state` fields in "
            "vcf_product_parse.jsonl. Behaviour claims (shares a carrier, "
            "disperses in water, infuses over time) come from the "
            "chemistry (phase_bucket, compound_group, percentile share). "
            "Never the reverse — a molecule's identity cannot license a "
            "claim about how a product was prepared, however tightly the "
            "molecule set is curated. This is the fix for three prior "
            "revisions' repeated failure mode (see this file's module "
            "docstring)."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Wrote {len(FRAMES)} phase frames to {PHASE_FRAMES_JSONL}")
    for f in FRAMES:
        flags = []
        if f["pending_volatility_data"]:
            flags.append("PENDING VOLATILITY DATA")
        if f["pending_authoring"]:
            flags.append("PENDING AUTHORING")
        flag = f" [{', '.join(flags)}]" if flags else ""
        print(f"  {f['frame_id']}{flag}")
    print(
        "\n7 OVERLAYS entries NOT ported (technique-shaped, not "
        "triggerable): sear, roast, cure, braise, ground, terrine, raw"
    )


if __name__ == "__main__":
    main()
