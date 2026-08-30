"""
VCF Compound Layer — shared structured-trigger evaluator and description
generator, used by build_vcf_phase_frames.py (writes phase_frames.jsonl,
generates each frame's human-readable trigger_description from its
structured trigger) and build_vcf_competition.py (evaluates frame triggers
against real pair data to decide frame_id attachment).

--- Why this exists ---

Two revisions in a row produced a bug where the trigger's TEXT and the
trigger's EVALUATION diverged: Revision 1 attached a frame to pairs
missing a required compound group; Revision 2 attached it to pairs that
had the right group but not the right chemistry. In both cases the
trigger was a STRING that some other piece of code — hand-written Python
in build_vcf_competition.py — separately interpreted. Nothing enforced
that the string and the code agreed.

This module is the fix: a trigger is a structured JSON object, ONE
function (`evaluate_trigger`) is the only code that ever decides whether
a trigger fires, and `generate_trigger_description` produces the
human-readable form MECHANICALLY from the same structure, so there is no
second, hand-authored description to drift out of sync. A build-time and
test-time check (see build_vcf_phase_frames.py and
test_vcf_reliability.py) re-generates each frame's description from its
stored trigger and asserts it matches the stored trigger_description.

--- Trigger schema ---

    {"all": [<condition>, ...]}

Each condition is `{"field": <name>, <op>: <value>}` where op is one of:
    "eq"           field == value
    "in"           field in value (value is a list)
    "equals"       set(field) == set(value) — order-independent equality,
                    for a field whose VALUE is itself a small unordered
                    collection (e.g. group_pair); use "eq" instead for a
                    scalar
    "contains"     value in field (field is a set/list)
    "contains_any" any(v in field for v in value)
    "gte"          field >= value

--- Two kinds of context ---

A trigger is evaluated against a `context` dict:

  - PAIR context (used by build_vcf_competition.py for a two-product
    conflict): {"bucket": <str>, "groups_present": <set of str>,
    "group_pair": <2-item collection of str, the pair's own two dominant
    groups>, "a_group_percentile": <float>, "b_group_percentile": <float>,
    "sides": [<side dict>, <side dict>]}. Each side dict holds that
    product's own role_counts/role_shares plus any flat per-side fields a
    trigger references (e.g. "preparation", "group_percentile" — see
    either_side/other_side below).
  - SINGLE-PRODUCT context (declared for water_phase_dispersion_timing
    and fat_phase_long_infusion_volatility_split, not currently evaluated
    by any script — see those frames' notes in build_vcf_phase_frames.py):
    {"dominant_bucket": <str>, "volatility_buckets_present": <set of str>}.

--- Three field-scoping conventions ---

A field name is resolved by a fixed NAMING CONVENTION, not by anything in
the trigger JSON itself (there is no per-condition "scope" key):

  1. "role_counts.X" / "role_shares.X" — SIDE-SCOPED, SAME-SIDE. Evaluated
     against context["sides"]; satisfied only if AT LEAST ONE side
     satisfies ALL such conditions in the trigger TOGETHER (a
     "count>=8 on side A, share>=0.03 on side B" pairing would not be the
     same claim as "count>=8 AND share>=0.03 on the SAME side," so this
     evaluator deliberately does not allow that).

  2. "either_side.X" / "other_side.X" — SIDE-SCOPED, COMPLEMENTARY-SIDE.
     Also evaluated against context["sides"] (exactly 2 sides required),
     but the two prefixes name DIFFERENT sides of the SAME pair: an
     "either_side.X" condition and an "other_side.Y" condition together
     are satisfied if there exists an assignment of the pair's two sides
     to (either, other) — either order — such that the "either_side"
     conditions all hold on the side assigned "either" and the
     "other_side" conditions all hold on the OTHER side. This is for a
     claim like "one side is smoked AND the other side is a terpene-heavy
     carrier" — a relationship BETWEEN the two sides, not a property that
     can hold on either side independently (unlike case 1 above). The
     leading "either_side."/"other_side." is stripped before looking the
     remaining field name up directly on that side's dict (a flat lookup,
     not the dotted role_counts/role_shares nesting of case 1) — e.g.
     "either_side.preparation" resolves to side["preparation"].

  3. Everything else is PAIR-SCOPED — resolved directly against the
     top-level context (bucket, groups_present, group_pair,
     a_group_percentile, b_group_percentile, dominant_bucket,
     volatility_buckets_present).
"""
from __future__ import annotations


def _resolve_pair_field(context, field):
    if field == "bucket":
        return context.get("bucket")
    if field == "groups_present":
        return context.get("groups_present")
    if field == "group_pair":
        return context.get("group_pair")
    if field == "a_group_percentile":
        return context.get("a_group_percentile")
    if field == "b_group_percentile":
        return context.get("b_group_percentile")
    if field == "dominant_bucket":
        return context.get("dominant_bucket")
    if field == "volatility_buckets_present":
        return context.get("volatility_buckets_present")
    raise ValueError(f"Unknown pair/single-context trigger field: {field!r}")


def _is_side_scoped(field: str) -> bool:
    """Same-side scoping (case 1 in the module docstring) — role_counts.*
    and role_shares.* only. either_side./other_side. are a DIFFERENT
    scoping (case 2) and are checked separately; see _is_either_other."""
    return field.startswith("role_counts.") or field.startswith("role_shares.")


def _is_either_other(field: str) -> bool:
    return field.startswith("either_side.") or field.startswith("other_side.")


def _side_value(side, field):
    """Resolve a same-side-scoped field (role_counts.X / role_shares.X) —
    dotted, nested lookup."""
    top, key = field.split(".", 1)
    return side.get(top, {}).get(key)


def _either_other_side_value(side, field):
    """Resolve an either_side.X / other_side.X field — the prefix names
    WHICH side to try (handled by the caller), and the remainder is a
    flat key on that side's dict, not a nested lookup."""
    _prefix, key = field.split(".", 1)
    return side.get(key)


def _condition_holds_for_value(value, cond):
    if "eq" in cond:
        return value == cond["eq"]
    if "in" in cond:
        return value in cond["in"]
    if "equals" in cond:
        return value is not None and set(value) == set(cond["equals"])
    if "contains" in cond:
        return value is not None and cond["contains"] in value
    if "contains_any" in cond:
        return value is not None and any(v in value for v in cond["contains_any"])
    if "gte" in cond:
        return value is not None and value >= cond["gte"]
    raise ValueError(f"Unsupported condition operator in {cond!r}")


def evaluate_trigger(context, trigger) -> bool:
    if "all" not in trigger:
        raise ValueError(f"Unsupported trigger shape (expected top-level 'all'): {trigger!r}")

    all_conditions = trigger["all"]
    pair_conditions = [c for c in all_conditions if not _is_side_scoped(c["field"]) and not _is_either_other(c["field"])]
    side_conditions = [c for c in all_conditions if _is_side_scoped(c["field"])]
    either_conditions = [c for c in all_conditions if c["field"].startswith("either_side.")]
    other_conditions = [c for c in all_conditions if c["field"].startswith("other_side.")]

    for cond in pair_conditions:
        value = _resolve_pair_field(context, cond["field"])
        if not _condition_holds_for_value(value, cond):
            return False

    if side_conditions:
        sides = context.get("sides")
        if not sides:
            raise ValueError(
                "Trigger has side-scoped condition(s) (role_counts.*/role_shares.*) "
                "but context has no 'sides' — this trigger requires a PAIR context."
            )
        if not any(
            all(_condition_holds_for_value(_side_value(side, c["field"]), c) for c in side_conditions)
            for side in sides
        ):
            return False

    if either_conditions or other_conditions:
        sides = context.get("sides")
        if not sides or len(sides) != 2:
            raise ValueError(
                "Trigger has either_side.*/other_side.* condition(s) but "
                "context doesn't have exactly 2 sides — this trigger "
                "requires a 2-sided PAIR context."
            )

        def _assignment_holds(side_either, side_other):
            return all(
                _condition_holds_for_value(_either_other_side_value(side_either, c["field"]), c)
                for c in either_conditions
            ) and all(
                _condition_holds_for_value(_either_other_side_value(side_other, c["field"]), c)
                for c in other_conditions
            )

        if not (_assignment_holds(sides[0], sides[1]) or _assignment_holds(sides[1], sides[0])):
            return False

    return True


def _describe_condition(cond) -> str:
    field = cond["field"]
    if "eq" in cond:
        return f"{field} == {cond['eq']!r}"
    if "in" in cond:
        return f"{field} in {cond['in']!r}"
    if "equals" in cond:
        return f"{field} == {cond['equals']!r}"
    if "contains" in cond:
        return f"{field} contains {cond['contains']!r}"
    if "contains_any" in cond:
        return f"{field} contains any of {cond['contains_any']!r}"
    if "gte" in cond:
        return f"{field} >= {cond['gte']!r}"
    raise ValueError(f"Unsupported condition operator in {cond!r}")


def generate_trigger_description(trigger) -> str:
    """Mechanically stringify a structured trigger — never hand-author
    this text separately; see module docstring."""
    if "all" not in trigger:
        raise ValueError(f"Unsupported trigger shape: {trigger!r}")
    all_conditions = trigger["all"]
    pair_parts = [_describe_condition(c) for c in all_conditions if not _is_side_scoped(c["field"]) and not _is_either_other(c["field"])]
    side_parts = [_describe_condition(c) for c in all_conditions if _is_side_scoped(c["field"])]
    either_parts = [_describe_condition(c) for c in all_conditions if c["field"].startswith("either_side.")]
    other_parts = [_describe_condition(c) for c in all_conditions if c["field"].startswith("other_side.")]

    parts = list(pair_parts)
    if side_parts:
        parts.append("(" + " AND ".join(side_parts) + ") on at least one side")
    if either_parts or other_parts:
        parts.append(
            "(" + " AND ".join(either_parts) + ") on one side AND "
            "(" + " AND ".join(other_parts) + ") on the other side"
        )
    return " AND ".join(parts)
