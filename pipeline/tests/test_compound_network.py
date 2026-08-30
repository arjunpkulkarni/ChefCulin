"""Flavor compound network lookup tests."""
import pytest

from culin_etl.compound_network import (
    display_name,
    is_same_base,
    network_token,
    top_compound_neighbors,
)


@pytest.fixture
def sample_compound_rows():
    return [
        {"seed": "garlic", "neighbor": "white_wine", "display": "White Wine", "weight": 53, "confidence": 0.5},
        {"seed": "garlic", "neighbor": "beer", "display": "Beer", "weight": 46, "confidence": 0.45},
        {"seed": "garlic", "neighbor": "roasted_chicken", "display": "Roasted Chicken", "weight": 33, "confidence": 0.3},
        {"seed": "chicken", "neighbor": "fried_chicken", "display": "Fried Chicken", "weight": 123, "confidence": 0.9},
        {"seed": "chicken", "neighbor": "roasted_beef", "display": "Roasted Beef", "weight": 100, "confidence": 0.8},
        {"seed": "chicken", "neighbor": "pork_sausage", "display": "Pork Sausage", "weight": 84, "confidence": 0.7},
        {"seed": "chicken", "neighbor": "white_wine", "display": "White Wine", "weight": 20, "confidence": 0.2},
    ]


def test_network_token_foodb_names():
    assert network_token("Chicken") == "chicken"
    assert network_token("Garlic") == "garlic"
    assert network_token("Cattle (Beef, Veal)") == "beef"
    assert network_token("Sweet orange") == "orange"


def test_display_name():
    assert display_name("white_wine") == "White Wine"


def test_is_same_base_filters_chicken_variants():
    assert is_same_base("chicken", "fried_chicken")
    assert is_same_base("chicken", "roasted_chicken")
    assert not is_same_base("garlic", "white_wine")


def test_top_neighbors_garlic(sample_compound_rows):
    canon, rows = top_compound_neighbors(sample_compound_rows, "Garlic", n=5)
    assert canon == "garlic"
    names = [r["ingredient"] for r in rows]
    assert "white_wine" in names
    assert "garlic" not in names


def test_top_neighbors_chicken_excludes_cuts(sample_compound_rows):
    _, rows = top_compound_neighbors(sample_compound_rows, "Chicken", n=8)
    for r in rows:
        assert "chicken" not in r["ingredient"] or r["ingredient"] == "chicken_broth"
