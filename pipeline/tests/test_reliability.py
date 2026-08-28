"""Dataset reliability — artifacts must match vendor source and culinary anchors."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from culin_etl.api import DEFAULT_COMPOUND, load_compound_tables
from culin_etl.build import load_artifact_tables
from culin_etl.compound_network import index_neighbors, top_compound_neighbors
from culin_etl.lookup import index_cooccur, top_cooccur
from culin_etl.vendor_paths import EDGES_CSV

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "artifacts" / "corpus"
COMPOUND = DEFAULT_COMPOUND


def _vendor_garlic_top(n: int = 8) -> list[tuple[str, int]]:
    rows = []
    with EDGES_CSV.open(encoding="utf-8") as f:
        for a, b, w in csv.reader(f):
            if a == "garlic":
                rows.append((b, int(w)))
            elif b == "garlic":
                rows.append((a, int(w)))
    rows.sort(key=lambda x: (-x[1], x[0]))
    return rows[:n]


@pytest.fixture(scope="module")
def corpus_tables():
    if not (CORPUS / "cooccur.jsonl").exists():
        pytest.skip("corpus artifacts missing — run npm run build or copy artifacts")
    return load_artifact_tables(CORPUS)


@pytest.fixture(scope="module")
def compound_tables():
    if not (COMPOUND / "neighbors.jsonl").exists():
        pytest.skip("compound artifacts missing — run npm run build:compound")
    return load_compound_tables(COMPOUND)


def test_vendor_edges_csv_present():
    assert EDGES_CSV.is_file()
    lines = EDGES_CSV.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 90_000


def test_corpus_artifact_scale(corpus_tables):
    assert len(corpus_tables["cooccur"]) >= 10_000
    assert len(corpus_tables["ingredient_technique"]) >= 1_000


def test_compound_artifact_scale(compound_tables):
    assert len(compound_tables["neighbors"]) >= 5_000
    meta = compound_tables.get("meta") or {}
    if meta:
        assert meta.get("neighbor_rows", 0) >= 5_000


def test_garlic_compound_matches_vendor(compound_tables):
    vendor_top = _vendor_garlic_top(8)
    assert vendor_top[0][0] == "white_wine"
    assert vendor_top[0][1] == 53

    canon, rows = top_compound_neighbors(compound_tables["neighbors"], "Garlic", n=8)
    assert canon == "garlic"
    assert len(rows) >= 5
    tokens = [r["ingredient"] for r in rows]
    assert "white_wine" in tokens
    assert "beer" in tokens
    assert tokens[0] == "white_wine"
    assert rows[0]["weight"] == vendor_top[0][1]


def test_compound_neighbors_sorted_by_weight(compound_tables):
    idx = index_neighbors(compound_tables["neighbors"])
    for seed in ("garlic", "chicken", "apple"):
        if seed not in idx:
            continue
        weights = [r["weight"] for r in idx[seed]]
        assert weights == sorted(weights, reverse=True)


def test_cooccur_garlic_corpus_anchors(corpus_tables):
    rows = top_cooccur(corpus_tables["cooccur"], "garlic", n=12)
    names = [r["ingredient"] for r in rows]
    assert len(names) >= 5
    assert "olive oil" in names
    assert "oregano" in names
    conf = [r["confidence"] for r in rows]
    assert conf == sorted(conf, reverse=True)


def test_cooccur_duck_corpus_anchors(corpus_tables):
    rows = top_cooccur(corpus_tables["cooccur"], "duck", n=10)
    names = [r["ingredient"] for r in rows]
    assert "onion" in names
    assert "butter" in names


def test_cooccur_index_matches_scan(corpus_tables):
    """Indexed lookup must agree with full-table scan."""
    idx = index_cooccur(corpus_tables["cooccur"])
    for seed in ("garlic", "duck", "chicken"):
        direct = top_cooccur(corpus_tables["cooccur"], seed, n=6)
        via_idx = idx.get(seed, [])[:6]
        assert [r["ingredient"] for r in direct] == [r["ingredient"] for r in via_idx]


def test_compound_api_matches_tables(compound_tables):
    """FastAPI compound route must match in-process lookup."""
    from fastapi.testclient import TestClient

    from culin_etl.api import create_app

    app = create_app(compound=compound_tables)
    client = TestClient(app)
    res = client.get("/compound", params={"ingredient": "Garlic", "n": 8}).json()
    assert res["canonical"] == "garlic"
    tokens = [r["ingredient"] for r in res["results"]]
    assert "white_wine" in tokens
