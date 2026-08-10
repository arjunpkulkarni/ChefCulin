"""Given an ingredient, return top-N co-occurring ingredients with freq/confidence."""

from culin_etl.lookup import top_cooccur


def test_duck_top_includes_orange_butter_thyme(artifacts):
    rows = top_cooccur(artifacts["cooccur"], "duck", n=10)
    names = [r["ingredient"] for r in rows]
    assert "orange" in names
    assert "butter" in names
    assert "thyme" in names


def test_duck_does_not_rank_sprinkles(artifacts):
    rows = top_cooccur(artifacts["cooccur"], "duck", n=10)
    names = [r["ingredient"] for r in rows]
    assert "sprinkles" not in names


def test_row_shape_and_sort(artifacts):
    rows = top_cooccur(artifacts["cooccur"], "garlic", n=5)
    assert len(rows) <= 5
    assert rows, "garlic should have neighbors in the fixture"
    for r in rows:
        assert set(r) >= {"ingredient", "freq", "confidence"}
        assert r["ingredient"] != "garlic"
        assert r["freq"] >= 1
        assert isinstance(r["confidence"], float)
    confs = [r["confidence"] for r in rows]
    assert confs == sorted(confs, reverse=True)


def test_chicken_neighbors_are_savory(artifacts):
    rows = top_cooccur(artifacts["cooccur"], "chicken", n=10)
    names = set(r["ingredient"] for r in rows)
    assert {"lemon", "garlic", "thyme"} & names
    assert "sprinkles" not in names
    assert "cocoa" not in names


def test_tomato_canonical_in_graph(artifacts):
    # tomato variants should appear as canonical "tomato", not three spellings
    ings = set()
    for e in artifacts["cooccur"]:
        ings.add(e["a"])
        ings.add(e["b"])
    assert "tomato" in ings
    assert "tomatoes" not in ings
    assert "roma tomato" not in ings
    assert "cherry tomatoes" not in ings
