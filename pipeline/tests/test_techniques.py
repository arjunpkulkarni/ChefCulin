"""Given an ingredient, return top-N associated techniques with freq/confidence."""

from culin_etl.lookup import top_techniques
from culin_etl.techniques import TECHNIQUE_VOCAB, extract_techniques


def test_controlled_vocab_includes_core_methods():
    for t in ("sear", "roast", "braise", "fry", "simmer", "confit", "bake"):
        assert t in TECHNIQUE_VOCAB


def test_extract_from_duck_steps():
    steps = [
        "Sear the duck breasts skin-side down until crisp.",
        "Roast in the oven until medium-rare.",
        "Reduce orange juice with butter for the sauce.",
    ]
    found = extract_techniques(steps)
    assert "sear" in found
    assert "roast" in found
    assert "reduce" in found


def test_duck_techniques(artifacts):
    rows = top_techniques(artifacts["ingredient_technique"], "duck", n=10)
    names = [r["technique"] for r in rows]
    assert "sear" in names
    assert "roast" in names
    assert "frost" not in names
    assert "blend" not in names


def test_short_ribs_braise(artifacts):
    rows = top_techniques(artifacts["ingredient_technique"], "short ribs", n=5)
    names = [r["technique"] for r in rows]
    assert names[0] == "braise" or "braise" in names


def test_potato_roast_or_fry(artifacts):
    rows = top_techniques(artifacts["ingredient_technique"], "potato", n=10)
    names = set(r["technique"] for r in rows)
    assert {"roast", "fry"} & names


def test_technique_row_shape(artifacts):
    rows = top_techniques(artifacts["ingredient_technique"], "duck", n=5)
    assert rows
    for r in rows:
        assert set(r) >= {"technique", "freq", "confidence"}
        assert r["freq"] >= 1
    confs = [r["confidence"] for r in rows]
    assert confs == sorted(confs, reverse=True)
