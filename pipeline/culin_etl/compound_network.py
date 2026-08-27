"""
Flavor compound network — shared volatile-compound projection (Ahn et al. / FooDB).

Edge weight = count of shared flavor compounds between two ingredients.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional

# Preparation variants of the same base ingredient — not useful as compound suggestions.
_PREP_RE = re.compile(
    r"^(raw|fried|roasted|boiled|grilled|cured|baked|smoked|dried|pickled)_"
)


def network_token(name: str) -> str:
    """Map a display / Foodb name to the flavor-network underscore token."""
    raw = str(name or "").strip().lower()
    if not raw:
        return ""

    paren = re.search(r"\(([^)]+)\)", raw)
    if paren:
        parts = [p.strip() for p in re.split(r"[,/]", paren.group(1)) if p.strip()]
        for p in parts:
            if p in ("beef", "veal", "pork", "lamb", "mutton", "duck", "chicken", "turkey"):
                return "lamb" if p == "mutton" else p
        if "orange" in raw:
            return "orange"

    s = raw
    s = re.sub(r"\b(mallard|velvet|domestic|european|wild|sweet|sour|bitter)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" ", "_")
    s = re.sub(r"_+", "_", s).strip("_")

    aliases = {
        "cattle": "beef",
        "pig": "pork",
        "sheep": "lamb",
        "goat": "goat",
        "soy_bean": "soybean",
        "soy_sauce": "soy_sauce",
    }
    return aliases.get(s, s)


def display_name(token: str) -> str:
    """`white_wine` → `White wine`."""
    return " ".join(w.capitalize() for w in str(token or "").split("_") if w)


def is_same_base(seed: str, neighbor: str) -> bool:
    """Drop fried_chicken when seed is chicken, etc."""
    if not seed or not neighbor:
        return False
    if seed == neighbor:
        return True
    s, n = seed.lower(), neighbor.lower()
    if s in n or n in s:
        return True
    for prep in ("raw", "fried", "roasted", "boiled", "grilled", "cured", "baked", "smoked"):
        if n == f"{prep}_{s}" or s == f"{prep}_{n}":
            return True
    return False


def index_neighbors(rows: list[dict]) -> Dict[str, List[dict]]:
    """seed token → sorted neighbor rows (weight desc)."""
    idx: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        seed = row["seed"]
        idx[seed].append(
            {
                "ingredient": row["neighbor"],
                "display": row.get("display") or display_name(row["neighbor"]),
                "weight": row["weight"],
                "confidence": row.get("confidence", 0),
            }
        )
    for key in idx:
        idx[key].sort(
            key=lambda r: (-r["weight"], -r["confidence"], r["ingredient"])
        )
    return dict(idx)


def top_compound_neighbors(
    rows: list[dict],
    ingredient: str,
    n: int = 24,
    index: Dict[str, List[dict]] | None = None,
    *,
    exclude: Optional[set[str]] = None,
) -> tuple[str, list[dict]]:
    """
    Return (canonical_seed, neighbors) for a focus ingredient.
    Tries exact token, then strips preparation prefixes.
    """
    exclude = exclude or set()
    token = network_token(ingredient)
    idx = index if index is not None else index_neighbors(rows)

    candidates = [token]
    m = _PREP_RE.match(token)
    if m:
        candidates.append(token[m.end() :])
    if token.endswith("_broth"):
        candidates.append(token.replace("_broth", ""))

    for key in candidates:
        if not key or key not in idx:
            continue
        out = []
        for row in idx[key]:
            nb = row["ingredient"]
            if is_same_base(key, nb):
                continue
            if nb in exclude or row["display"].lower() in {e.lower() for e in exclude}:
                continue
            out.append(row)
            if len(out) >= n:
                break
        if out:
            return key, out

    return token, []
