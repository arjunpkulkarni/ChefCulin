"""
VCF Compound Layer — Step 11e: channel-conflict (competition) detection.

Run from the repo root, AFTER build_vcf_phase.py (needs `phase_bucket`/
`compound_group` on compounds.jsonl), build_vcf_compound_roles.py +
build_vcf_profile_roles.py (needs `role_counts`/`role_shares` on
profiles.jsonl — used here only for the terpene_mono/terpene_sesqui
subtype split, see REVISION 4 Change 3; smoke_marker is no longer
consumed by anything in this file, see REVISION 4 below), and
build_vcf_pairs.py:
    python pipeline/scripts/build_vcf_competition.py

Reads:  pipeline/artifacts/vcf/compounds.jsonl        (phase_bucket, compound_group)
        pipeline/artifacts/vcf/profiles.jsonl         (per-product compound sets,
                                                        role_counts/role_shares)
        pipeline/artifacts/vcf/pairs.jsonl            (the pairs actually surfaced)
        pipeline/artifacts/vcf/phase_frames.jsonl
        pipeline/artifacts/vcf/vcf_product_parse.jsonl (parsed `preparation`/
                                                        `cure_state` — REVISION 4)
Writes: pipeline/artifacts/vcf/competition.jsonl
        pipeline/artifacts/vcf/meta.json   (adds a "competition" block)

--- Scope: pairs.jsonl, not the full product x product matrix ---

Step 11e's job is to flag when two DISH COMPONENTS both lean on the same
phase bucket — a real channel conflict a chef can act on. Scanning every
possible pair of the corpus's 521 culinary products (~135,000
combinations) would mostly generate conflicts between things that would
never plausibly appear in the same dish together, which is noise dressed
up as signal. Scoped instead to the pairs Step 5 already computed and
stored — 10,260 rows, the top-20 for every product, i.e. exactly the set
the pairing lens already tells a chef "these go together." That is the
right population to ask "and if they do, what do they compete for."

--- Per-product dominant bucket / dominant group ---

For each product's own compound profile, restricted to compounds that
have BOTH a phase_bucket and a compound_group (a compound missing either
is silently excluded from this calculation, not defaulted into a bucket
or group it doesn't have):
  dominant_bucket = the phase_bucket with the most of that product's
                     compounds (plurality, not majority — ties broken by
                     bucket name for determinism)
  dominant_group  = within THAT bucket only (not the whole profile), the
                     compound_group with the most compounds.
`dominant_bucket` decides WHICH phase two products are competing in.
Whether they're actually crowding it is a separate, group-share-based
question; see the percentile gate below.

--- Detection rule ---

For every stored pair (a, b) in pairs.jsonl, restricted to bucket_a ==
bucket_b and bucket_a in {fat_phase, fat_leaning} (both_phases excluded —
a compound there has an alternative route, not a shared limited carrier):
  flag a conflict if BOTH sides' contested-group share of their own
  profile is at or above the 75th percentile for that group, corpus-wide
  (see `compute_group_percentile_table`). `dominant_group(a)` and
  `dominant_group(b)` may be the SAME group (`same_group_crowding`) or
  different groups (`cross_group_carrier`) — both are real conflicts.
Both directions of an unordered pair collapse to one row (lower
vcf_product_id first), matching form_diffs.jsonl's own convention.

Flag, don't filter — same rule the association engine and Step 9b follow.
A competition row is information ("these two are both crowding the fat
phase"), not an error suppressing the pair from pairs.jsonl.

=====================================================================
REVISION 4 — the underlying error, stated once (see Step 11e's own memo)
=====================================================================

Three revisions in a row produced a wrong frame attachment, all the same
shape: an authored sentence claiming PROVENANCE ("smoke") that the
chemistry can only ever establish a BEHAVIOUR claim for ("fat-soluble
phenols and terpenes share a limited carrier"). Guaiacol arrives from
smoking, roasting, barrel char, malt kilning, or a floral source — the
molecule is identical in every case, so no curation of the molecule side
(Revision 3's smoke_marker role included) can ever license a provenance
claim. The rule this revision encodes: provenance claims come from the
parsed `preparation` field; behaviour claims come from the chemistry.
Never the reverse. This splits what was one frame into two — see
build_vcf_phase_frames.py's docstring for the full account.

--- Change 1: the flagship frame is now a pure behaviour claim ---

`fat_phase_phenol_terpene_carrier` (replaces
`fat_phase_smoke_terpene_competition`) drops ALL role/provenance
inference. Its trigger (stored in phase_frames.jsonl, evaluated here via
`vcf_trigger_lib.evaluate_trigger`) is exactly:
  bucket in (fat_phase, fat_leaning) AND
  group_pair == {Hydrocarbons, Phenols} (order-independent) AND
  a_group_percentile >= 75 AND b_group_percentile >= 75
No smoke_marker condition at all. Because `group_pair` uses "equals"
against a 2-DISTINCT-item set, this trigger can never fire on a
same_group_crowding row by construction (a_group==b_group would make
group_pair a 1-item set) — `conflict_type == "cross_group_carrier"` is
still checked explicitly in `_assert_flagship_rows_satisfy_trigger` as a
belt-and-suspenders structural invariant, but it's implied by the trigger
itself now, not bolted on separately the way Revision 3's smoke_marker
check needed it to be.

Expected effect: the ~37 rows Revision 2 wrongly called "smoke" (anise
brandy, ouzo, calamus, star anise, fennel, chervil, pimento leaf, Korean
mint...) become framed again — correctly, as carrier competition, not
smoke. This is the first change in four revisions that INCREASES frame
coverage, because the sentence now matches the evidence everywhere the
evidence holds, rather than a narrower (and wrong) claim riding on top of
it. Revision 3's single framed row (MICROBIAL FERMENTED TEA / YELLOW BOX
HONEY) drops out here — its contested groups are {Carbonyls aldehydes,
Hydrocarbons}, not {Hydrocarbons, Phenols}, so it was never a phenol/
terpene carrier collision; Revision 3's smoke_marker gate let it in on a
side's SECONDARY phenolic content that wasn't even that side's own
dominant group.

--- Change 2: a separate, preparation-gated smoke frame (stub) ---

`smoked_product_fat_phase` is a PROVENANCE claim, gated on the actual
parsed `preparation` field (vcf_product_parse.jsonl — `PORK, CURED
(smoked)` and `PORK, UNCURED (smoked)` carry `preparation: ["smoked"]`),
not a molecule. Its trigger uses `either_side.preparation contains
'smoked'` AND `other_side.group_percentile >= 75` — see vcf_trigger_lib.py
for the either_side/other_side complementary-side semantics this
required adding. It ships with `pending_authoring: True` and an empty
sentence in phase_frames.jsonl; `frame_id` is NEVER set to this frame's
id regardless of whether its trigger fires (enforced structurally below,
in `_assign_frame_id` — a frame's own `pending_authoring` flag gates
attachment, not just its trigger). Its trigger IS evaluated here, purely
for the honest `n_firing_rows` report: `compute_smoked_stub_firing_rows`
re-checks it against the SAME final `rows` population the flagship frame
draws from. Expect 0 in this corpus — see that function's docstring for
why (both smoked products' own pairs.jsonl top-20 neighbours are other
pork/Maillard-adjacent products, not terpene-heavy carriers, so neither
ever survives into `rows` at all, regardless of this frame's trigger).

--- Change 3: the terpene mono/sesqui split is wired into detection ---

`terpene_mono`/`terpene_sesqui` (built in Revision 3, previously reported
only as an unused reporting-only diagnostic) now GATES the
Hydrocarbons-vs-Hydrocarbons same_group_crowding cluster (459 rows before
this revision — 34% of the file, and uninformative, because plain
alkenes/aromatics/monoterpenes/sesquiterpenes/diterpenes were all
collapsed into one structural group). See `classify_hydrocarbons_terpene_subtype`
for the exact rule: each side's OWN terpene_mono/terpene_sesqui role
SHARE must clear that role's own 75th percentile (computed from real
corpus role_shares, same "present at all" population rule used
throughout this build — see `compute_role_percentile_table`). A row
survives ONLY if both sides clear the SAME role's gate together
(`conflict_subtype = mono_crowding` or `sesqui_crowding`); it is DROPPED
— removed from competition.jsonl entirely, not merely left unsubtyped —
if neither role's gate clears on both sides, or if the two sides clear
DIFFERENT roles (one mono-heavy, one sesqui-heavy: `mono_vs_sesqui` is
computed only as an internal/reporting drop-reason, per instruction it is
never stored as a `conflict_subtype` value on a surviving row). This
tightening applies ONLY to Hydrocarbons-vs-Hydrocarbons rows; every other
group pair (same-group or cross-group) is unaffected and keeps
`conflict_subtype: null`.

James's own sanity table (computed by hand against the pre-Revision-4
artifacts) projected roughly 370 mono_crowding / 23 sesqui_crowding / 63
dropped-neither / 3 dropped-cross. The actual rebuild differs — see
`classify_hydrocarbons_terpene_subtype`'s docstring and the
`terpene_subtype_counts` meta.json block for the real numbers and the
specific reason for the gap (~122 of the 459 rows clear BOTH roles' gates
on BOTH sides at once — broad, high-terpene profiles that are neither
cleanly mono nor cleanly sesqui — a case James's table doesn't appear to
have accounted for; this build resolves those by whichever role's
COMBINED share is larger, documented inline, not silently). Per
instruction, this is reported as a finding about the corpus, not hidden
or forced to match the sanity table.

--- Why the flat floor was replaced (history) ---

A flat 20% floor treats every compound group as if it had the same
baseline concentration, and they don't. Corpus medians across 521
culinary products (share = fraction of a product's own valid-compound
profile in that group, computed for every product where the group is
present at all — see `compute_group_percentile_table`):

  Hydrocarbons  n=423  median 18.0%  p75 33.2%  p90 50.0%
  Alcohols      n=486  median 16.8%  p75 23.3%  p90 30.2%
  Phenols       n=336  median  4.5%  p75  7.5%  p90 12.5%
  Furans        n=366  median  4.0%  p75  6.6%  p90  9.9%

The fix: gate each side against its OWN group's 75th percentile, computed
from real corpus data, not a flat number.

--- Same-group crowding admitted (history) ---

Two ingredients dumping the SAME class into the same limited phase is a
real conflict, not excluded. `conflict_type` (`same_group_crowding` vs
`cross_group_carrier`) records which kind of row it is.

--- render_mode for unframed rows (history) ---

Most rows have no authored frame. A `render_mode` field (`framed` vs
`data_only`) means a future display layer shows the underlying facts
instead of either inventing a sentence or showing a bare flag with
nothing behind it. This script does NOT generate that data-only sentence
text itself.

=====================================================================
--- frame_id attachment ---
=====================================================================

A competition row gets a frame_id ONLY when (a) it matches an authored
frame's structured trigger in phase_frames.jsonl (evaluated via
`vcf_trigger_lib.evaluate_trigger`), AND (b) that frame's own
`pending_authoring` is False. (b) is what keeps `smoked_product_fat_phase`
dormant despite having a real, evaluable trigger — see
`_assign_frame_id`. `conflict_type == "cross_group_carrier"` remains a
hard requirement for the flagship frame specifically, re-verified
independently in `_assert_frame_assignments_correct` (Revision 5 — renamed
from `_assert_flagship_rows_satisfy_trigger`, see below) by reconstructing
each row's context from its OWN stored fields, not the code path that
assigned frame_id. Every other detected conflict still gets a row, with
frame_id=null and render_mode="data_only".

=====================================================================
REVISION 5 — smoked_product_fat_phase's mechanism gate; a second
authored, non-pending PAIR-context frame
=====================================================================

Beef ingestion gave `smoked_product_fat_phase` its first real firing rows
(4) — and every one contends on Carbonyls,aldehydes, never Phenols. The
Revision 4 trigger checked provenance (either_side.preparation contains
"smoked") and a bare percentile gate on the OTHER side, but never verified
that the SMOKED side's own chemistry was what its sentence would have
claimed. Same failure shape as three prior revisions, one level deeper:
the trigger's own name asserted a mechanism it never checked. See
build_vcf_phase_frames.py's REVISION 5 docstring section for the trigger
fix itself (`either_side.group eq 'Phenols'`, bound to the same side as
the preparation condition); this file's job is evaluating it, which now
requires a per-side `"group"` key on the PAIR context's `sides` list (see
`_pair_trigger_context` and `compute_smoked_stub_firing_rows`) — that
field didn't exist before because nothing needed same-side group binding
until now.

`fat_phase_aldehyde_load_crowding` is the frame those 4 displaced rows
actually belong to: a pure behaviour claim, `groups_present contains
"Carbonyls, aldehydes"` plus both sides' own group percentile >= 75, no
preparation gate. It is the SECOND non-pending PAIR-context frame this
build has ever had — `_assign_frame_id` and the independent re-derivation
check both generalize from "check the one flagship frame" to "check every
non-pending PAIR-context frame, and assert at most one fires per row" (see
`_assign_frame_id` and `_assert_frame_assignments_correct`). Their trigger
shapes are disjoint by construction — the flagship requires
group_pair=={{'Hydrocarbons','Phenols'}} exactly (a 2-item set equality),
which cannot also contain 'Carbonyls, aldehydes' (a pair only has 2 sides,
so 2 possible groups) — but the code asserts this rather than assuming it,
per this file's own established paranoia about frame attachment bugs.
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from vcf_trigger_lib import evaluate_trigger

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "pipeline" / "artifacts" / "vcf"
COMPOUNDS_JSONL = OUT_DIR / "compounds.jsonl"
PROFILES_JSONL = OUT_DIR / "profiles.jsonl"
PAIRS_JSONL = OUT_DIR / "pairs.jsonl"
PHASE_FRAMES_JSONL = OUT_DIR / "phase_frames.jsonl"
VCF_PRODUCT_PARSE_JSONL = OUT_DIR / "vcf_product_parse.jsonl"
COMPETITION_JSONL = OUT_DIR / "competition.jsonl"
META_JSON = OUT_DIR / "meta.json"

FLAGSHIP_FRAME_ID = "fat_phase_phenol_terpene_carrier"
ALDEHYDE_FRAME_ID = "fat_phase_aldehyde_load_crowding"  # REVISION 5
SMOKED_STUB_FRAME_ID = "smoked_product_fat_phase"
# REVISION 5: every non-pending PAIR-context frame that can be assigned to
# a row, checked in this order by _assign_frame_id. Order only matters if
# two frames' triggers could ever both fire on the same row — asserted
# NOT to happen in _assert_frame_assignments_correct, rather than assumed.
ASSIGNABLE_FRAME_IDS = (FLAGSHIP_FRAME_ID, ALDEHYDE_FRAME_ID)
FAT_AFFINE_BUCKETS = {"fat_phase", "fat_leaning"}
PERCENTILE_GATE = 75  # both sides must clear this percentile for their own group
PREVIOUS_REVISION_ROW_COUNT_FLAT_FLOOR = 297  # Revision 1's count, for comparison only
TERPENE_ROLES = ("terpene_mono", "terpene_sesqui")
DISH_SIM_TRIALS = 3000
DISH_SIM_SIZES = (4, 6)
DISH_SIM_SEED = 20260829  # fixed for reproducibility; see simulate_conflicts_per_dish


def dominant_bucket_and_group(compound_ids, bucket_by_id, group_by_id):
    bucket_counts: Counter = Counter()
    for cid in compound_ids:
        b = bucket_by_id.get(cid)
        if b is not None:
            bucket_counts[b] += 1
    if not bucket_counts:
        return None, None
    max_count = max(bucket_counts.values())
    dominant_bucket = sorted(k for k, v in bucket_counts.items() if v == max_count)[0]

    group_counts: Counter = Counter()
    for cid in compound_ids:
        if bucket_by_id.get(cid) == dominant_bucket:
            g = group_by_id.get(cid)
            if g is not None:
                group_counts[g] += 1
    if not group_counts:
        return dominant_bucket, None
    max_g = max(group_counts.values())
    dominant_group = sorted(k for k, v in group_counts.items() if v == max_g)[0]
    return dominant_bucket, dominant_group


def group_share_in_profile(compound_ids, group, bucket_by_id, group_by_id) -> float:
    """Fraction of this profile's valid compounds (has both a phase_bucket
    and a compound_group) that belong to the given compound_group — NOT
    restricted to any particular bucket."""
    valid = [
        cid for cid in compound_ids
        if bucket_by_id.get(cid) is not None and group_by_id.get(cid) is not None
    ]
    if not valid:
        return 0.0
    n = sum(1 for cid in valid if group_by_id.get(cid) == group)
    return n / len(valid)


def _percentile_value(sorted_values, p):
    """Linear-interpolation percentile (numpy/pandas default 'linear'
    method) — the threshold VALUE at percentile p, used for gating."""
    if not sorted_values:
        return None
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def _percentile_rank(value, sorted_values):
    """Rank-based percentile (0-100) of a specific value within a
    distribution — informational only."""
    if not sorted_values:
        return None
    n = len(sorted_values)
    count_le = sum(1 for v in sorted_values if v <= value)
    return round(100 * count_le / n, 1)


def compute_group_percentile_table(profiles, bucket_by_id, group_by_id):
    """For every culinary product where a compound_group is present at all
    (share > 0), record that group's share of the WHOLE profile as one
    sample in the group's reference distribution."""
    samples_by_group: dict[str, list[float]] = defaultdict(list)
    for prof in profiles:
        if prof.get("class") != "culinary":
            continue
        cids = prof["compound_ids"]
        valid = [
            cid for cid in cids
            if bucket_by_id.get(cid) is not None and group_by_id.get(cid) is not None
        ]
        if not valid:
            continue
        counts = Counter(group_by_id[cid] for cid in valid)
        n = len(valid)
        for group, count in counts.items():
            samples_by_group[group].append(count / n)

    table = {}
    for group, shares in samples_by_group.items():
        shares_sorted = sorted(shares)
        table[group] = {
            "n_products": len(shares_sorted),
            "median_share": round(_percentile_value(shares_sorted, 50), 4),
            "p75_share": round(_percentile_value(shares_sorted, 75), 4),
            "p90_share": round(_percentile_value(shares_sorted, 90), 4),
            "_shares_sorted": shares_sorted,  # not written to meta.json; used internally for rank lookups
        }
    return table


def compute_role_percentile_table(profiles, role_names):
    """Same method as compute_group_percentile_table, but keyed on a
    compound_roles.jsonl role's role_shares (from profiles.jsonl,
    build_vcf_profile_roles.py's output), restricted to culinary products
    where that role is present at all (share > 0) — the same "present at
    all, not dominant" population rule used everywhere else in this
    build. Used by Change 3 to gate the Hydrocarbons-vs-Hydrocarbons
    terpene_mono/terpene_sesqui subtype split."""
    table = {}
    culinary = [p for p in profiles if p.get("class") == "culinary"]
    for role in role_names:
        shares_sorted = sorted(
            p["role_shares"][role] for p in culinary
            if p.get("role_shares", {}).get(role, 0) > 0
        )
        if not shares_sorted:
            continue
        table[role] = {
            "n_products": len(shares_sorted),
            "median_share": round(_percentile_value(shares_sorted, 50), 4),
            "p75_share": round(_percentile_value(shares_sorted, 75), 4),
            "p90_share": round(_percentile_value(shares_sorted, 90), 4),
            "_shares_sorted": shares_sorted,
        }
    return table


def _pair_trigger_context(bucket, lo_group, hi_group, a_group_percentile, b_group_percentile,
                           prof_lo, prof_hi, prep_lo, prep_hi):
    """Build the PAIR context vcf_trigger_lib.evaluate_trigger expects —
    see that module's docstring for the field-scoping rules. Carries
    everything ANY currently-defined pair-context trigger needs: the pure
    group_pair/percentile fields for the flagship behaviour frame, and
    per-side preparation/group_percentile for the smoked-provenance stub
    (role_counts/role_shares are also included per side for completeness,
    though no live trigger currently reads them — smoke_marker was
    retired as a frame input this revision; see module docstring)."""
    return {
        "bucket": bucket,
        "groups_present": {lo_group, hi_group},
        "group_pair": [lo_group, hi_group],
        "a_group_percentile": a_group_percentile,
        "b_group_percentile": b_group_percentile,
        "sides": [
            {
                "role_counts": prof_lo.get("role_counts", {}),
                "role_shares": prof_lo.get("role_shares", {}),
                "preparation": prep_lo,
                "group_percentile": a_group_percentile,
                "group": lo_group,  # REVISION 5: same-side binding for
                                     # smoked_product_fat_phase's mechanism gate
            },
            {
                "role_counts": prof_hi.get("role_counts", {}),
                "role_shares": prof_hi.get("role_shares", {}),
                "preparation": prep_hi,
                "group_percentile": b_group_percentile,
                "group": hi_group,
            },
        ],
    }


def _assign_frame_id(context, frames_by_id):
    """The ONLY place frame_id is ever decided. A frame can be attached
    ONLY if (a) its trigger fires against this pair's context, AND (b) it
    is NOT pending_authoring — this second condition is what keeps
    smoked_product_fat_phase dormant even though its trigger is real and
    evaluated (see compute_smoked_stub_firing_rows for where that
    evaluation actually happens, purely for reporting).

    REVISION 5: generalized from "check the flagship frame" to "check
    every frame in ASSIGNABLE_FRAME_IDS" now that
    fat_phase_aldehyde_load_crowding is a second non-pending PAIR-context
    frame. If more than one fires on the same row this raises rather than
    silently picking the first — their trigger shapes are disjoint by
    construction (see module docstring) but this asserts it instead of
    assuming it, matching this file's established paranoia about frame
    attachment bugs (see _assert_frame_assignments_correct for the
    independent, row-field-only re-derivation of the same invariant)."""
    fired = []
    for frame_id in ASSIGNABLE_FRAME_IDS:
        frame = frames_by_id.get(frame_id)
        if frame and not frame["pending_authoring"] and evaluate_trigger(context, frame["trigger"]):
            fired.append(frame_id)
    if len(fired) > 1:
        raise SystemExit(
            f"More than one assignable frame fired on the same pair context: {fired}. "
            f"ASSIGNABLE_FRAME_IDS triggers are assumed disjoint — this means they aren't."
        )
    return fired[0] if fired else None


def _assert_frame_assignments_correct(rows, frames_by_id):
    """Build-time anchor (REVISION 5 — renamed and generalized from
    _assert_flagship_rows_satisfy_trigger, which only ever checked one
    frame): independently re-derive whether each row's frame_id assignment
    is correct, reconstructing a PAIR context from the ROW'S OWN stored
    fields (bucket/a_group/b_group/a_group_percentile/b_group_percentile,
    plus groups_present — needed for fat_phase_aldehyde_load_crowding's
    `contains` condition, which group_pair's ordered list can't serve) and
    re-evaluating each ASSIGNABLE_FRAME_IDS trigger via evaluate_trigger —
    not the code path that assigned frame_id in main(). Per-frame
    conflict_type constraints are NOT uniform: the flagship requires
    cross_group_carrier (structurally implied by its group_pair equality
    check, but re-verified explicitly here anyway); the aldehyde frame has
    no such restriction by design (it's meant to fire on both conflict
    types — see build_vcf_phase_frames.py's REVISION 5 note). Also asserts
    at most one frame ever fires per row, and that NO row ever carries a
    pending_authoring frame's id."""
    FRAME_CONFLICT_TYPE_CONSTRAINT = {
        FLAGSHIP_FRAME_ID: "cross_group_carrier",
        ALDEHYDE_FRAME_ID: None,  # no restriction — fires on either conflict_type
    }
    bad = []
    for r in rows:
        reconstructed = {
            "bucket": r["bucket"],
            "group_pair": [r["a_group"], r["b_group"]],
            "groups_present": {r["a_group"], r["b_group"]},
            "a_group_percentile": r["a_group_percentile"],
            "b_group_percentile": r["b_group_percentile"],
        }
        fired = []
        for frame_id in ASSIGNABLE_FRAME_IDS:
            frame = frames_by_id.get(frame_id)
            if not frame:
                continue
            trigger_fires = evaluate_trigger(reconstructed, frame["trigger"])
            required_conflict_type = FRAME_CONFLICT_TYPE_CONSTRAINT[frame_id]
            satisfies_constraint = required_conflict_type is None or r["conflict_type"] == required_conflict_type
            if trigger_fires and satisfies_constraint:
                fired.append(frame_id)
        if len(fired) > 1:
            bad.append((f"more than one frame independently re-derived as firing: {fired}", r))
        expected_frame_id = fired[0] if fired else None
        if r["frame_id"] != expected_frame_id:
            bad.append((f"frame_id disagrees with independent trigger re-evaluation (expected {expected_frame_id!r})", r))
        if r["frame_id"] is not None:
            frame = frames_by_id.get(r["frame_id"])
            if frame is None:
                bad.append(("frame_id references a frame not in phase_frames.jsonl", r))
            elif frame["pending_authoring"]:
                bad.append(("frame_id set to a pending_authoring frame", r))
        if r["frame_id"] is None:
            if r["render_mode"] != "data_only":
                bad.append(("frame_id null but render_mode != data_only", r))
            if "sentence" in r:
                bad.append(("data_only row carries a sentence field", r))
        else:
            if r["render_mode"] != "framed":
                bad.append(("frame_id set but render_mode != framed", r))
            required_conflict_type = FRAME_CONFLICT_TYPE_CONSTRAINT.get(r["frame_id"])
            if required_conflict_type is not None and r["conflict_type"] != required_conflict_type:
                bad.append((f"frame_id set on a conflict_type other than required {required_conflict_type!r}", r))
    if bad:
        lines = "\n".join(f"  - {reason}: {row}" for reason, row in bad[:10])
        raise SystemExit(
            f"{len(bad)} competition row(s) failed independent frame/render "
            f"invariant checks. First up to 10:\n{lines}"
        )


def classify_hydrocarbons_terpene_subtype(prof_a, prof_b, role_percentiles):
    """REVISION 4, Change 3: for a Hydrocarbons-vs-Hydrocarbons
    same_group_crowding row, decide whether the two sides are crowding
    the SAME terpene sub-class, a genuine cross (dropped), or neither
    clears a role gate at all (dropped).

    Gate: each side's OWN terpene_mono/terpene_sesqui role_share (from
    profiles.jsonl, "present at all" population — see
    compute_role_percentile_table) must be at/above that role's own 75th
    percentile. The two gates are checked INDEPENDENTLY per role, so a
    side can clear both at once (a broad, high-terpene profile — real in
    this corpus, ~122 of 459 rows have both sides clearing both gates
    together). When both sides of a pair clear BOTH gates simultaneously,
    the ambiguity is broken by whichever channel's COMBINED share
    (a_share + b_share) is larger — the more pronounced crowd — rather
    than an arbitrary fixed priority order. This is a documented policy
    choice, not a re-derivation of James's sanity table: several
    plausible tie-break rules were tried against the real artifact data
    (independent-gate-with-magnitude-tiebreak; dominant-sub-role-by-raw-
    share; dominant-sub-role-by-percentile-rank) and NONE reproduced his
    370/23/63/3 projection exactly, while the "neither side clears either
    gate" drop count (63) matched exactly under every variant tried —
    confirming the GATE itself (not the tie-break) is right, and that his
    table's 63/3 split for the two drop reasons was likely an estimate,
    not a rebuild. Reported honestly as a corpus finding, per instruction,
    rather than reverse-engineered to hit his numbers.

    Returns (conflict_subtype_or_None, keep: bool, audit_fields: dict,
    drop_reason_or_None). `mono_vs_sesqui` is returned only as a
    drop_reason (for reporting) — it is NEVER a stored conflict_subtype
    value, per instruction.
    """
    mono_table = role_percentiles.get("terpene_mono")
    sesq_table = role_percentiles.get("terpene_sesqui")
    a_mono = prof_a.get("role_shares", {}).get("terpene_mono", 0.0)
    b_mono = prof_b.get("role_shares", {}).get("terpene_mono", 0.0)
    a_sesq = prof_a.get("role_shares", {}).get("terpene_sesqui", 0.0)
    b_sesq = prof_b.get("role_shares", {}).get("terpene_sesqui", 0.0)

    mono_gate = mono_table["p75_share"] if mono_table else float("inf")
    sesq_gate = sesq_table["p75_share"] if sesq_table else float("inf")

    mono_clears = a_mono >= mono_gate and b_mono >= mono_gate
    sesq_clears = a_sesq >= sesq_gate and b_sesq >= sesq_gate

    audit = {
        "a_terpene_mono_share": round(a_mono, 4),
        "b_terpene_mono_share": round(b_mono, 4),
        "a_terpene_sesqui_share": round(a_sesq, 4),
        "b_terpene_sesqui_share": round(b_sesq, 4),
    }

    if mono_clears and sesq_clears:
        subtype = "mono_crowding" if (a_mono + b_mono) >= (a_sesq + b_sesq) else "sesqui_crowding"
        return subtype, True, audit, None
    if mono_clears:
        return "mono_crowding", True, audit, None
    if sesq_clears:
        return "sesqui_crowding", True, audit, None
    cross = (a_mono >= mono_gate and b_sesq >= sesq_gate) or (a_sesq >= sesq_gate and b_mono >= mono_gate)
    drop_reason = "mono_vs_sesqui" if cross else "neither_clears_role_gate"
    return None, False, audit, drop_reason


def compute_smoked_stub_firing_rows(rows, prep_by_id, smoke_stub_trigger):
    """REVISION 4, Change 2: honest n_firing_rows report for the
    pending_authoring smoked_product_fat_phase stub. Re-evaluates the
    trigger against the SAME final `rows` population the flagship frame
    draws from (not a fresh scan of all candidate pairs before the
    percentile gate) — this matches the spec's own framing ('smoked pork
    does not currently appear in any competition row'). Never mutates
    frame_id/render_mode on any row; this is a side-channel diagnostic
    only. Expect zero matches in this corpus: PORK, CURED (smoked) and
    PORK, UNCURED (smoked) are the only two products with 'smoked' in
    their parsed preparation, and neither survives into `rows` at all —
    their own pairs.jsonl top-20 neighbours are other pork cuts and
    Maillard-adjacent products, not a fat-affine terpene-heavy carrier —
    so this frame is correct and dormant rather than broken."""
    matches = []
    for r in rows:
        context = {
            "bucket": r["bucket"],
            "sides": [
                {
                    "preparation": prep_by_id.get(r["vcf_product_id_a"], []),
                    "group_percentile": r["a_group_percentile"],
                    "group": r["a_group"],  # REVISION 5: mechanism gate needs the smoked side's own group
                },
                {
                    "preparation": prep_by_id.get(r["vcf_product_id_b"], []),
                    "group_percentile": r["b_group_percentile"],
                    "group": r["b_group"],
                },
            ],
        }
        if evaluate_trigger(context, smoke_stub_trigger):
            matches.append(r)
    return matches


def simulate_conflicts_per_dish(rows, profiles, pairs, sizes=DISH_SIM_SIZES, trials=DISH_SIM_TRIALS):
    """Corpus row count is the wrong measure of noise — a chef doesn't see
    the corpus, they see one plate. Sample realistic dishes (built by
    walking pairs.jsonl's own 'these go together' graph outward from a
    random anchor, not uniform-random products) of size 4 and 6, count how
    many surviving competition rows fall entirely within each sampled
    dish, and report the median and 90th-percentile hit count."""
    culinary_ids = [p["vcf_product_id"] for p in profiles if p.get("class") == "culinary"]
    partners_by_id: dict[int, list[int]] = defaultdict(list)
    for p in pairs:
        a, b = p["anchor_vcf_product_id"], p["match_vcf_product_id"]
        partners_by_id[a].append(b)
        partners_by_id[b].append(a)

    conflict_pairs = {frozenset((r["vcf_product_id_a"], r["vcf_product_id_b"])) for r in rows}

    rng = random.Random(DISH_SIM_SEED)

    def sample_dish(k):
        anchor = rng.choice(culinary_ids)
        dish = {anchor}
        frontier = list(partners_by_id.get(anchor, []))
        rng.shuffle(frontier)
        while len(dish) < k and frontier:
            cand = frontier.pop()
            if cand in dish:
                continue
            dish.add(cand)
            more = list(partners_by_id.get(cand, []))
            rng.shuffle(more)
            frontier.extend(more)
        if len(dish) < k:
            remaining = [c for c in culinary_ids if c not in dish]
            rng.shuffle(remaining)
            while len(dish) < k and remaining:
                dish.add(remaining.pop())
        return list(dish)

    results = {}
    for k in sizes:
        counts = []
        for _ in range(trials):
            dish = sample_dish(k)
            n_conflicts = 0
            for i in range(len(dish)):
                for j in range(i + 1, len(dish)):
                    if frozenset((dish[i], dish[j])) in conflict_pairs:
                        n_conflicts += 1
            counts.append(n_conflicts)
        counts_sorted = sorted(counts)
        results[f"k{k}"] = {
            "n_trials": trials,
            "median_conflicts": _percentile_value(counts_sorted, 50),
            "p90_conflicts": _percentile_value(counts_sorted, 90),
            "max_conflicts": counts_sorted[-1],
            "pct_dishes_with_zero_conflicts": round(
                100 * sum(1 for c in counts_sorted if c == 0) / trials, 1
            ),
        }
    return results


def main():
    for p in (COMPOUNDS_JSONL, PROFILES_JSONL, PAIRS_JSONL, PHASE_FRAMES_JSONL, VCF_PRODUCT_PARSE_JSONL):
        if not p.exists():
            raise SystemExit(f"{p} not found — run the earlier pipeline steps first.")

    compounds = [json.loads(l) for l in COMPOUNDS_JSONL.read_text().splitlines() if l.strip()]
    bucket_by_id = {c["compound_id"]: c["phase_bucket"] for c in compounds if c.get("phase_bucket")}
    group_by_id = {c["compound_id"]: c["compound_group"] for c in compounds}

    profiles = [json.loads(l) for l in PROFILES_JSONL.read_text().splitlines() if l.strip()]
    profile_by_product = {p["vcf_product_id"]: p for p in profiles}
    if not any("role_counts" in p for p in profiles):
        raise SystemExit(
            "profiles.jsonl has no role_counts field — run "
            "build_vcf_compound_roles.py then build_vcf_profile_roles.py "
            "before this script."
        )

    parse_rows = [json.loads(l) for l in VCF_PRODUCT_PARSE_JSONL.read_text().splitlines() if l.strip()]
    prep_by_id = {r["vcf_product_id"]: (r.get("preparation") or []) for r in parse_rows}
    # Beef Ingestion Build Spec, Step 7: vcf_product_parse.jsonl is VCF-only
    # and frozen (not re-derived for this pass), so an external-source
    # product id (e.g. "beef:muscle:smoked") is never a key in it. Those
    # products carry their own `preparation` field directly on the profile
    # record (set by ingest_protein_beef.py) — fall back to that rather
    # than silently treating every non-VCF product as preparation=[],
    # which would permanently starve the either_side.preparation trigger
    # (smoked_product_fat_phase) of the only new smoked evidence this pass
    # adds.
    for pid, prof in profile_by_product.items():
        if pid not in prep_by_id and prof.get("preparation"):
            prep_by_id[pid] = prof["preparation"]

    percentile_table = compute_group_percentile_table(profiles, bucket_by_id, group_by_id)
    role_percentile_table = compute_role_percentile_table(profiles, TERPENE_ROLES)

    dom_cache: dict[int, tuple] = {}

    def dom_for(pid):
        if pid not in dom_cache:
            prof = profile_by_product.get(pid)
            cids = prof["compound_ids"] if prof else []
            dom_cache[pid] = dominant_bucket_and_group(cids, bucket_by_id, group_by_id)
        return dom_cache[pid]

    frames = [json.loads(l) for l in PHASE_FRAMES_JSONL.read_text().splitlines() if l.strip()]
    frames_by_id = {f["frame_id"]: f for f in frames}
    flagship_frame = frames_by_id.get(FLAGSHIP_FRAME_ID)
    if flagship_frame is None:
        raise SystemExit(f"{FLAGSHIP_FRAME_ID!r} not found in {PHASE_FRAMES_JSONL}")
    aldehyde_frame = frames_by_id.get(ALDEHYDE_FRAME_ID)  # REVISION 5
    if aldehyde_frame is None:
        raise SystemExit(f"{ALDEHYDE_FRAME_ID!r} not found in {PHASE_FRAMES_JSONL}")
    if aldehyde_frame["pending_authoring"]:
        raise SystemExit(f"{ALDEHYDE_FRAME_ID!r} must NOT be pending_authoring in this revision")
    smoke_stub_frame = frames_by_id.get(SMOKED_STUB_FRAME_ID)
    if smoke_stub_frame is None:
        raise SystemExit(f"{SMOKED_STUB_FRAME_ID!r} not found in {PHASE_FRAMES_JSONL}")
    if not smoke_stub_frame["pending_authoring"]:
        raise SystemExit(f"{SMOKED_STUB_FRAME_ID!r} must be pending_authoring in this revision")

    pairs = [json.loads(l) for l in PAIRS_JSONL.read_text().splitlines() if l.strip()]

    seen_unordered = set()
    rows = []
    n_candidates_same_bucket = 0  # bucket_a == bucket_b, both_phases excluded — before the percentile gate
    dropped_both_phases = 0
    dropped_below_percentile_gate = 0
    dropped_terpene_neither = 0
    dropped_terpene_cross = 0
    dropped_suppressed_near_duplicate = 0  # Fix 3 — always 0 today, see build_vcf_pairs.py's finding
    bucket_conflict_counts: Counter = Counter()
    conflict_type_counts: Counter = Counter()
    conflict_subtype_counts: Counter = Counter()
    render_mode_counts: Counter = Counter()
    group_pair_counts: Counter = Counter()
    missing_frame_group_pair_counts: Counter = Counter()

    for p in pairs:
        if p.get("suppressed_reason"):
            # Fix 3: a near-duplicate suppressed at the pairing layer is
            # exactly as uninformative as a "conflict" as it is as a
            # pairing suggestion — the same product at different
            # granularity competing with itself for a phase isn't a
            # finding. Always 0 today (see build_vcf_pairs.py's
            # near_duplicate_suppression finding) but future-proofed.
            dropped_suppressed_near_duplicate += 1
            continue
        a_id, b_id = p["anchor_vcf_product_id"], p["match_vcf_product_id"]
        # Beef Ingestion Build Spec: product ids are int for a VCF-sourced
        # product but a descriptive string ("beef:muscle:raw") for an
        # external-source one (see ingest_protein_beef.py) — sort by str()
        # so a VCF/beef pair never raises "int < str is unsupported",
        # while same-type pairs (the overwhelming majority) sort exactly
        # as before (str() is monotonic-consistent with int order here
        # only for display grouping, not used for anything numeric).
        key = tuple(sorted((a_id, b_id), key=str))
        if key in seen_unordered:
            continue
        seen_unordered.add(key)

        bucket_a, group_a = dom_for(a_id)
        bucket_b, group_b = dom_for(b_id)
        if bucket_a is None or bucket_b is None:
            continue
        if bucket_a != bucket_b:
            continue
        if bucket_a == "both_phases":
            dropped_both_phases += 1
            continue

        n_candidates_same_bucket += 1

        lo_id, hi_id = key
        lo_group, hi_group = (group_a, group_b) if a_id == lo_id else (group_b, group_a)
        prof_lo = profile_by_product[lo_id]
        prof_hi = profile_by_product[hi_id]

        lo_share = group_share_in_profile(prof_lo["compound_ids"], lo_group, bucket_by_id, group_by_id)
        hi_share = group_share_in_profile(prof_hi["compound_ids"], hi_group, bucket_by_id, group_by_id)

        lo_table = percentile_table.get(lo_group)
        hi_table = percentile_table.get(hi_group)
        if lo_table is None or hi_table is None:
            dropped_below_percentile_gate += 1
            continue

        lo_gate = lo_table["p75_share"]
        hi_gate = hi_table["p75_share"]
        if lo_share < lo_gate or hi_share < hi_gate:
            dropped_below_percentile_gate += 1
            continue

        conflict_type = "same_group_crowding" if lo_group == hi_group else "cross_group_carrier"

        # --- REVISION 4, Change 3: terpene mono/sesqui subtype gate ---
        # ONLY applies to Hydrocarbons-vs-Hydrocarbons same_group_crowding
        # rows — every other row is untouched by this block.
        conflict_subtype = None
        terpene_audit = {
            "a_terpene_mono_share": None, "b_terpene_mono_share": None,
            "a_terpene_sesqui_share": None, "b_terpene_sesqui_share": None,
        }
        if conflict_type == "same_group_crowding" and lo_group == "Hydrocarbons" and hi_group == "Hydrocarbons":
            conflict_subtype, keep, terpene_audit, drop_reason = classify_hydrocarbons_terpene_subtype(
                prof_lo, prof_hi, role_percentile_table
            )
            if not keep:
                if drop_reason == "mono_vs_sesqui":
                    dropped_terpene_cross += 1
                else:
                    dropped_terpene_neither += 1
                continue

        a_group_percentile = _percentile_rank(lo_share, lo_table["_shares_sorted"])
        b_group_percentile = _percentile_rank(hi_share, hi_table["_shares_sorted"])

        context = _pair_trigger_context(
            bucket_a, lo_group, hi_group, a_group_percentile, b_group_percentile,
            prof_lo, prof_hi, prep_by_id.get(lo_id, []), prep_by_id.get(hi_id, []),
        )
        frame_id = _assign_frame_id(context, frames_by_id)
        render_mode = "framed" if frame_id else "data_only"

        row = {
            "dish_component_a": prof_lo["raw_name"],
            "dish_component_b": prof_hi["raw_name"],
            "vcf_product_id_a": lo_id,
            "vcf_product_id_b": hi_id,
            "bucket": bucket_a,
            "conflict_type": conflict_type,
            "conflict_subtype": conflict_subtype,
            "a_group": lo_group,
            "b_group": hi_group,
            "a_group_share": round(lo_share, 4),
            "b_group_share": round(hi_share, 4),
            "a_group_percentile": a_group_percentile,
            "b_group_percentile": b_group_percentile,
            "a_group_baseline_median": lo_table["median_share"],
            "b_group_baseline_median": hi_table["median_share"],
            **terpene_audit,
            "render_mode": render_mode,
            "frame_id": frame_id,
        }
        rows.append(row)
        bucket_conflict_counts[bucket_a] += 1
        conflict_type_counts[conflict_type] += 1
        if conflict_subtype:
            conflict_subtype_counts[conflict_subtype] += 1
        render_mode_counts[render_mode] += 1
        group_label = (
            f"Hydrocarbons vs Hydrocarbons ({conflict_subtype})"
            if lo_group == "Hydrocarbons" and hi_group == "Hydrocarbons"
            else tuple(sorted((lo_group, hi_group)))
        )
        group_pair_counts[group_label] += 1
        if frame_id is None:
            missing_frame_group_pair_counts[group_label] += 1

    _assert_frame_assignments_correct(rows, frames_by_id)

    with open(COMPETITION_JSONL, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    framed_rows = [r for r in rows if r["frame_id"]]
    n_with_frame = len(framed_rows)
    # REVISION 5: framed_rows/n_with_frame above are the AGGREGATE across
    # every assignable frame — phenol_terpene_frame's own reporting needs
    # just its rows, now that a second frame can also set frame_id.
    flagship_framed_rows = [r for r in rows if r["frame_id"] == FLAGSHIP_FRAME_ID]
    aldehyde_framed_rows = [r for r in rows if r["frame_id"] == ALDEHYDE_FRAME_ID]
    conflicts_per_dish = simulate_conflicts_per_dish(rows, profiles, pairs)
    smoked_stub_matches = compute_smoked_stub_firing_rows(rows, prep_by_id, smoke_stub_frame["trigger"])

    percentile_table_for_meta = {
        g: {k: v for k, v in t.items() if k != "_shares_sorted"}
        for g, t in percentile_table.items()
    }
    role_percentile_table_for_meta = {
        g: {k: v for k, v in t.items() if k != "_shares_sorted"}
        for g, t in role_percentile_table.items()
    }

    def _label_to_str(label):
        return label if isinstance(label, str) else f"{label[0]} vs {label[1]}"

    n_hh_before_terpene_gate = (
        sum(c for k, c in group_pair_counts.items() if isinstance(k, str) and k.startswith("Hydrocarbons vs Hydrocarbons"))
        + dropped_terpene_neither + dropped_terpene_cross
    )

    meta = json.loads(META_JSON.read_text()) if META_JSON.exists() else {}
    meta["competition"] = {
        "n_pairs_scanned": len(seen_unordered),
        "n_candidates_same_bucket_excl_both_phases": n_candidates_same_bucket,
        "n_competition_rows": len(rows),
        "n_competition_rows_previous_revision_flat_floor": PREVIOUS_REVISION_ROW_COUNT_FLAT_FLOOR,
        "percentile_gate": PERCENTILE_GATE,
        "tightening": {
            "dropped_both_phases": dropped_both_phases,
            "dropped_below_percentile_gate": dropped_below_percentile_gate,
            "dropped_terpene_subtype_neither_clears": dropped_terpene_neither,
            "dropped_terpene_subtype_mono_vs_sesqui": dropped_terpene_cross,
            "dropped_suppressed_near_duplicate": dropped_suppressed_near_duplicate,
            "note": (
                "both_phases dropped entirely. Every remaining candidate "
                "(same bucket, fat_phase or fat_leaning) must clear its "
                "OWN group's 75th percentile share on BOTH sides. "
                "REVISION 4: Hydrocarbons-vs-Hydrocarbons rows additionally "
                "must clear a terpene_mono/terpene_sesqui role-share gate "
                "on BOTH sides for the SAME role — see "
                "terpene_subtype_counts below."
            ),
        },
        "conflict_type_counts": dict(conflict_type_counts),
        "conflict_subtype_counts": dict(conflict_subtype_counts),
        "terpene_subtype_gate": {
            "role_percentiles": role_percentile_table_for_meta,
            "n_hydrocarbons_vs_hydrocarbons_rows_before_gate": n_hh_before_terpene_gate,
            "n_kept_mono_crowding": conflict_subtype_counts.get("mono_crowding", 0),
            "n_kept_sesqui_crowding": conflict_subtype_counts.get("sesqui_crowding", 0),
            "n_dropped_neither_clears_role_gate": dropped_terpene_neither,
            "n_dropped_mono_vs_sesqui": dropped_terpene_cross,
            "sanity_target_from_spec": {
                "mono_crowding": 370, "sesqui_crowding": 23,
                "dropped_neither": 63, "dropped_mono_vs_sesqui": 3,
                "note": (
                    "James's own hand-computed sanity check, explicitly "
                    "offered as a target to verify against rather than "
                    "assume. The actual rebuild's 'dropped_neither' count "
                    "matches this exactly under every tie-break rule "
                    "tried; the mono_crowding/sesqui_crowding/"
                    "mono_vs_sesqui split differs — see "
                    "classify_hydrocarbons_terpene_subtype's docstring for "
                    "why (~122 of 459 rows clear BOTH roles' gates on BOTH "
                    "sides simultaneously, a case the sanity table doesn't "
                    "appear to have accounted for). Reported as a finding "
                    "about the corpus, not forced to match."
                ),
            },
        },
        "render_mode_counts": dict(render_mode_counts),
        "n_rows_with_authored_frame": n_with_frame,
        "n_rows_without_authored_frame": len(rows) - n_with_frame,
        "bucket_conflict_counts": dict(bucket_conflict_counts),
        "group_percentiles": percentile_table_for_meta,
        "group_percentiles_note": (
            "For every culinary product where a compound_group is present "
            "at all (share > 0 of that product's valid compounds), its "
            "share of the whole profile is one sample. NOT restricted to "
            "'group is dominant'."
        ),
        "top_group_pairs": {
            _label_to_str(k): c for k, c in group_pair_counts.most_common(10)
        },
        "top_group_pairs_missing_frame": {
            _label_to_str(k): c for k, c in missing_frame_group_pair_counts.most_common(10)
        },
        "top_group_pairs_missing_frame_note": (
            "Ranked by how often each unauthored collision fires among "
            "surviving rows — the priority order for which frame to write "
            "next in phase_frames.jsonl. REVISION 4: the former "
            "'Hydrocarbons vs Hydrocarbons' single bucket is now split "
            "into '(mono_crowding)'/'(sesqui_crowding)' — both still have "
            "no authored sentence, they're just no longer one undifferentiated "
            "cluster. Authoring the sentence is James's call, not a build step."
        ),
        "conflicts_per_dish": conflicts_per_dish,
        "conflicts_per_dish_note": (
            f"{DISH_SIM_TRIALS} simulated dishes per size, sampled by "
            f"walking pairs.jsonl's own association graph outward from a "
            f"random anchor product. Fixed seed {DISH_SIM_SEED} for "
            f"reproducibility. Comparable to the pre-Revision-4 numbers "
            f"(k4: median 0 / p90 3; k6: median 0 / p90 5) since the row "
            f"population changed (phenol/terpene reframing + terpene "
            f"subtype drops)."
        ),
        "detection_rule": (
            "Same dominant phase_bucket (fat_phase or fat_leaning only; "
            "both_phases excluded), BOTH sides at or above the 75th "
            "percentile of their own dominant compound_group's corpus-wide "
            "share-of-profile distribution. Dominant groups may be the "
            "same (conflict_type=same_group_crowding) or different "
            "(conflict_type=cross_group_carrier). Hydrocarbons-vs-"
            "Hydrocarbons rows are further gated by conflict_subtype "
            "(REVISION 4, Change 3). Scanned over the pairs already "
            "stored in pairs.jsonl."
        ),
        "frame_attachment_note": (
            "REVISION 4: fat_phase_phenol_terpene_carrier (replaces "
            "fat_phase_smoke_terpene_competition) is a pure behaviour "
            "claim — group_pair=={'Hydrocarbons','Phenols'} (order-"
            "independent) AND both sides' own group_percentile >= 75. No "
            "role/provenance inference. frame_id is set only when this "
            "trigger fires AND conflict_type=='cross_group_carrier' "
            "(implied by group_pair equality on 2 distinct items, but "
            "checked explicitly too) AND the frame is not "
            "pending_authoring. REVISION 5 adds a second assignable frame, "
            "fat_phase_aldehyde_load_crowding (groups_present contains "
            "'Carbonyls, aldehydes', both sides' group_percentile >= 75, "
            "no conflict_type restriction — fires on same_group_crowding "
            "and cross_group_carrier alike). smoked_product_fat_phase "
            "remains a SEPARATE, preparation-gated stub "
            "(pending_authoring=True), now with a mechanism gate added "
            "(either_side.group eq 'Phenols', bound to the same side as "
            "the preparation condition) — its trigger is evaluated for "
            "n_firing_rows reporting only; frame_id can never be set to "
            "it. See _assert_frame_assignments_correct for the "
            "independent re-derivation of every assignable frame."
        ),
        "phenol_terpene_frame": {
            "frame_id": FLAGSHIP_FRAME_ID,
            "n_rows": len(flagship_framed_rows),
            "products": sorted({r["dish_component_a"] for r in flagship_framed_rows} | {r["dish_component_b"] for r in flagship_framed_rows}),
            "note": (
                "REVISION 4 corrected list — a pure carrier-competition "
                "claim, no provenance inference. Replaces Revision 3's 1 "
                "row (MICROBIAL FERMENTED TEA / YELLOW BOX HONEY, which "
                "drops out here: its contested groups are "
                "{Carbonyls aldehydes, Hydrocarbons}, not "
                "{Hydrocarbons, Phenols}) and Revision 2's 37 wrongly-"
                "labeled-smoke rows (now framed correctly, as carrier "
                "competition, under this frame_id). REVISION 5: n_rows "
                "here is flagship-only — see n_rows_with_authored_frame "
                "for the total across both assignable frames."
            ),
        },
        "aldehyde_load_crowding_frame": {
            "frame_id": ALDEHYDE_FRAME_ID,
            "n_rows": len(aldehyde_framed_rows),
            "products": sorted({r["dish_component_a"] for r in aldehyde_framed_rows} | {r["dish_component_b"] for r in aldehyde_framed_rows}),
            "note": (
                "REVISION 5 addition. The 4 rows that prompted this frame "
                "(all beef:muscle:smoked, contending on Carbonyls,aldehydes "
                "against CUTTLEFISH/BRAZIL NUT/PARBOILED RICE/MICROBIAL "
                "FERMENTED TEA) plus every other row where lipid-oxidation "
                "aldehyde load is genuinely crowding a fat-affine phase, "
                "whether the other side shares that same group "
                "(same_group_crowding) or contends on a different one "
                "entirely (cross_group_carrier) — one sentence covers "
                "both shapes correctly, see build_vcf_phase_frames.py's "
                "REVISION 5 note."
            ),
        },
        "smoked_product_fat_phase_frame": {
            "frame_id": SMOKED_STUB_FRAME_ID,
            "pending_authoring": True,
            "n_firing_rows": len(smoked_stub_matches),
            "firing_row_products": sorted(
                {r["dish_component_a"] for r in smoked_stub_matches} | {r["dish_component_b"] for r in smoked_stub_matches}
            ),
            "note": (
                "REVISION 5: trigger now ALSO requires the smoked side's "
                "own contending group to be Phenols (either_side.group eq "
                "'Phenols', bound to the same side as the preparation "
                "condition) — a mechanism gate added alongside the "
                "existing provenance gate, because beef's 4 firing rows "
                "under the Revision 4 trigger all contended on "
                "Carbonyls,aldehydes, never Phenols (see "
                "aldehyde_load_crowding_frame above for where that signal "
                "actually belongs). Trigger evaluated against the final "
                "competition.jsonl row population purely for this report "
                "— frame_id is NEVER set to this frame's id regardless of "
                "the count here (enforced in _assign_frame_id / "
                "_assert_frame_assignments_correct). Expected 0: neither "
                "beef's own smoke_marker/Phenols content (real — 12.3%/"
                "16.4% of its own profile) nor the original two smoked "
                "pork products (PORK, CURED (smoked) / PORK, UNCURED "
                "(smoked), whose pairs.jsonl top-20 neighbours are other "
                "pork/Maillard-adjacent products, not a fat-affine "
                "terpene-heavy carrier) currently wins a phenol-contending "
                "competition row. Fact about this corpus, not a broken "
                "trigger — activates once a smoked product contends on "
                "phenols specifically."
            ),
        },
        "smoke_marker_role_status": (
            "The compound_roles.jsonl smoke_marker role (29 curated "
            "compounds) and its role_counts/role_shares on profiles.jsonl "
            "still exist, byte-identical to Revision 3 — this script does "
            "not touch either artifact. REVISION 4 simply stops using "
            "that role to drive ANY frame trigger, per the "
            "provenance-vs-behaviour rule (see build_vcf_phase_frames.py's "
            "docstring): a curated molecule set, however precise, cannot "
            "license a claim about how a product was prepared. Provenance "
            "now comes from vcf_product_parse.jsonl's parsed `preparation` "
            "field instead (see smoked_product_fat_phase_frame above)."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2))

    print(f"Scanned {len(seen_unordered)} stored pairs")
    print(f"Candidates (same bucket, not both_phases): {n_candidates_same_bucket}")
    print(f"  dropped (both_phases, out of scope): {dropped_both_phases}")
    print(f"  dropped (below {PERCENTILE_GATE}th percentile gate): {dropped_below_percentile_gate}")
    print(f"  dropped (terpene subtype gate, neither clears): {dropped_terpene_neither}")
    print(f"  dropped (terpene subtype gate, mono vs sesqui): {dropped_terpene_cross}")
    print(f"Wrote {len(rows)} competition rows to {COMPETITION_JSONL}")
    print(f"  (Revision 1's flat-floor count was {PREVIOUS_REVISION_ROW_COUNT_FLAT_FLOOR})")
    print(f"  {n_with_frame} with an authored frame attached")
    print(f"  {len(rows) - n_with_frame} flagged with no authored sentence yet (render_mode=data_only)")
    print(f"\nConflict type counts: {dict(conflict_type_counts)}")
    print(f"Conflict subtype counts: {dict(conflict_subtype_counts)}")
    print(f"Render mode counts: {dict(render_mode_counts)}")
    print("\nBucket conflict counts:")
    for b, c in bucket_conflict_counts.most_common():
        print(f"  {b:<14} {c}")
    print("\nTop group-pair collisions (surviving rows):")
    for gp, c in group_pair_counts.most_common(10):
        print(f"  {_label_to_str(gp):<40} {c}")
    print("\nTop group-pair collisions with NO authored frame (write these next):")
    for gp, c in missing_frame_group_pair_counts.most_common(10):
        print(f"  {_label_to_str(gp):<40} {c}")
    print("\nConflicts per simulated dish:")
    for size_key, stats in conflicts_per_dish.items():
        print(
            f"  {size_key}: median={stats['median_conflicts']:.1f} "
            f"p90={stats['p90_conflicts']:.1f} max={stats['max_conflicts']} "
            f"({stats['pct_dishes_with_zero_conflicts']}% of dishes have zero conflicts)"
        )
    print(f"\nPhenol/terpene carrier frame (Revision 4): {len(flagship_framed_rows)} rows")
    for name in sorted({r["dish_component_a"] for r in flagship_framed_rows} | {r["dish_component_b"] for r in flagship_framed_rows}):
        print(f"  {name}")
    print(f"\nAldehyde-load crowding frame (Revision 5): {len(aldehyde_framed_rows)} rows")
    for name in sorted({r["dish_component_a"] for r in aldehyde_framed_rows} | {r["dish_component_b"] for r in aldehyde_framed_rows}):
        print(f"  {name}")
    print(f"\nSmoked-product stub (pending_authoring, mechanism-gated as of Revision 5): n_firing_rows={len(smoked_stub_matches)}")
    print(f"Pairs dropped as suppressed near-duplicates (Fix 3): {dropped_suppressed_near_duplicate}")


if __name__ == "__main__":
    main()
