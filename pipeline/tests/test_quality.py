"""Dedupe near-identical recipes; filter spam/low-quality entries."""

from culin_etl.quality import is_low_quality
from culin_etl.parse import Recipe


def test_empty_recipe_is_low_quality():
    r = Recipe(
        id="x",
        title="Empty Junk",
        ingredients=[],
        directions=[],
        ner=[],
        link="",
        source="",
    )
    assert is_low_quality(r) is True


def test_too_thin_recipe_is_low_quality():
    r = Recipe(
        id="x",
        title="Too Thin",
        ingredients=["salt"],
        directions=["Serve."],
        ner=["salt"],
        link="",
        source="",
    )
    assert is_low_quality(r) is True


def test_near_duplicate_duck_recipes_collapsed(artifacts):
    # Fixture has Seared Duck with Orange + an exact copy.
    # After dedupe, duck should still co-occur with orange, but recipe count
    # for that pair must not be inflated by the duplicate.
    duck_orange = next(
        e for e in artifacts["cooccur"] if e["a"] == "duck" and e["b"] == "orange"
    )
    # 3 distinct duck+orange recipes in fixture (ids 0,1,2); copy of 0 dropped
    assert duck_orange["freq"] == 3


def test_build_drops_junk(artifacts):
    titles = {r["title"] for r in artifacts["recipes"]}
    assert "Empty Junk" not in titles
    assert "Too Thin" not in titles
