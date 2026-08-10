from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from culin_etl.normalize import canonicalize


def index_cooccur(edges: list[dict]) -> Dict[str, List[dict]]:
    """ingredient → sorted neighbor rows (confidence desc)."""
    idx: Dict[str, List[dict]] = defaultdict(list)
    for e in edges:
        row_ab = {
            "ingredient": e["b"],
            "freq": e["freq"],
            "confidence": e["confidence"],
        }
        row_ba = {
            "ingredient": e["a"],
            "freq": e["freq"],
            "confidence": e["confidence"],
        }
        idx[e["a"]].append(row_ab)
        idx[e["b"]].append(row_ba)
    for key in idx:
        idx[key].sort(key=lambda r: (-r["confidence"], -r["freq"], r["ingredient"]))
    return dict(idx)


def index_techniques(edges: list[dict]) -> Dict[str, List[dict]]:
    """ingredient → sorted technique rows (confidence desc)."""
    idx: Dict[str, List[dict]] = defaultdict(list)
    for e in edges:
        idx[e["ingredient"]].append(
            {
                "technique": e["technique"],
                "freq": e["freq"],
                "confidence": e["confidence"],
            }
        )
    for key in idx:
        idx[key].sort(key=lambda r: (-r["confidence"], -r["freq"], r["technique"]))
    return dict(idx)


def top_cooccur(
    edges: list[dict],
    ingredient: str,
    n: int = 10,
    index: Dict[str, List[dict]] | None = None,
) -> list[dict]:
    key = canonicalize(ingredient) or ingredient.strip().lower()
    if index is not None:
        return index.get(key, [])[:n]
    hits: list[dict] = []
    for e in edges:
        if e["a"] == key:
            other = e["b"]
        elif e["b"] == key:
            other = e["a"]
        else:
            continue
        hits.append(
            {
                "ingredient": other,
                "freq": e["freq"],
                "confidence": e["confidence"],
            }
        )
    hits.sort(key=lambda r: (-r["confidence"], -r["freq"], r["ingredient"]))
    return hits[:n]


def top_techniques(
    edges: list[dict],
    ingredient: str,
    n: int = 10,
    index: Dict[str, List[dict]] | None = None,
) -> list[dict]:
    key = canonicalize(ingredient) or ingredient.strip().lower()
    if index is not None:
        return index.get(key, [])[:n]
    hits = [
        {
            "technique": e["technique"],
            "freq": e["freq"],
            "confidence": e["confidence"],
        }
        for e in edges
        if e["ingredient"] == key
    ]
    hits.sort(key=lambda r: (-r["confidence"], -r["freq"], r["technique"]))
    return hits[:n]
