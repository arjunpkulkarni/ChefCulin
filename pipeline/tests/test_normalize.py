"""Normalization collapses obvious duplicates (acceptance)."""

from culin_etl.normalize import canonicalize


def test_tomato_variants_collapse():
    variants = [
        "tomatoes",
        "roma tomato",
        "cherry tomatoes",
        "1 can diced tomatoes",
        "Tomato",
    ]
    assert {canonicalize(v) for v in variants} == {"tomato"}


def test_potato_variants_collapse():
    assert canonicalize("potatoes") == "potato"
    assert canonicalize("yukon potatoes") == "potato"


def test_strips_quantity_and_unit():
    assert canonicalize("2 tbsp butter") == "butter"
    assert canonicalize("1 cup orange juice") == "orange"


def test_chicken_forms():
    assert canonicalize("chicken breasts") == "chicken"
    assert canonicalize("whole chicken") == "chicken"


def test_empty_and_junk():
    assert canonicalize("") is None
    assert canonicalize("   ") is None
