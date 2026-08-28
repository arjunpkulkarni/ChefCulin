"""Balance axis derivation from FooDB compound mapping."""

from __future__ import annotations

from culin_etl.balance_axes import (
    build_foodb_balance_rows,
    classify_compound,
    lookup_compound_profile,
    load_compound_profiles,
)


def test_classify_glutamic_acid():
    axes = classify_compound("l glutamic acid")
    assert axes.get("glut", 0) >= 1.0


def test_classify_capsaicin():
    axes = classify_compound("capsaicin")
    assert axes.get("capsaicin", 0) >= 1.0


def test_classify_acetic_acid():
    axes = classify_compound("acetic acid")
    assert axes.get("acid", 0) >= 1.0


def test_apple_has_acid_from_compounds():
    profiles = load_compound_profiles()
    raw = lookup_compound_profile("Apple", profiles)
    assert raw.get("acid", 0) > 0


def test_build_foodb_balance_has_coverage():
    rows, meta = build_foodb_balance_rows()
    assert meta["foodb_count"] == 933
    assert meta["compound_backed"] >= 500
    assert meta.get("content_backed", 0) >= 400
    by_name = {r["name"]: r for r in rows}
    assert by_name["Lemon"]["axes"].get("acid", 0) > 0
    assert by_name["Chicken"]["axes"].get("nucl", 0) > 0
    soy = by_name["Soy sauce"]["axes"]
    assert soy.get("salt", 0) > 0.5
    assert soy.get("glut", 0) > 0.3
