from __future__ import annotations

import re

# Longest-first alias keys so "cherry tomatoes" wins over "tomatoes"
ALIASES: list[tuple[str, str]] = [
    ("cherry tomatoes", "tomato"),
    ("roma tomato", "tomato"),
    ("diced tomatoes", "tomato"),
    ("tomatoes", "tomato"),
    ("tomato", "tomato"),
    ("yukon potatoes", "potato"),
    ("potatoes", "potato"),
    ("potato", "potato"),
    ("chicken breasts", "chicken"),
    ("whole chicken", "chicken"),
    ("chicken", "chicken"),
    ("beef short ribs", "short ribs"),
    ("short ribs", "short ribs"),
    ("orange juice", "orange"),
    ("orange zest", "orange"),
    ("oranges", "orange"),
    ("orange", "orange"),
    ("duck breasts", "duck"),
    ("duck breast", "duck"),
    ("whole duck", "duck"),
    ("duck", "duck"),
    ("olive oil", "olive oil"),
    ("red wine", "red wine"),
    ("thyme sprigs", "thyme"),
    ("fresh thyme", "thyme"),
]

UNIT_WORDS = {
    "c",
    "cup",
    "cups",
    "tbsp",
    "tsp",
    "teaspoon",
    "teaspoons",
    "tablespoon",
    "tablespoons",
    "oz",
    "ounce",
    "ounces",
    "lb",
    "lbs",
    "pound",
    "pounds",
    "g",
    "kg",
    "ml",
    "l",
    "can",
    "cans",
    "jar",
    "package",
    "pkg",
    "clove",
    "cloves",
    "slice",
    "slices",
    "piece",
    "pieces",
    "pinch",
    "dash",
}

STOP_MODIFIERS = {
    "fresh",
    "large",
    "small",
    "medium",
    "boneless",
    "skinless",
    "chopped",
    "minced",
    "diced",
    "sliced",
    "crushed",
    "ground",
    "dried",
    "whole",
    "firmly",
    "packed",
    "broken",
    "bite",
    "size",
    "shredded",
    "optional",
    "and",
    "or",
    "to",
    "taste",
    "a",
    "an",
    "the",
    "of",
}

_QTY = re.compile(
    r"^[\d\s\/\.\-½¼¾⅓⅔⅛⅜⅝⅞]+"
)
_NON_ALNUM = re.compile(r"[^a-z0-9\s\-]")


def _strip_qty_units(text: str) -> str:
    t = text.lower().strip()
    t = _NON_ALNUM.sub(" ", t)
    t = _QTY.sub(" ", t)
    tokens = [tok for tok in t.split() if tok and tok not in UNIT_WORDS]
    tokens = [tok for tok in tokens if tok not in STOP_MODIFIERS]
    return " ".join(tokens).strip()


def canonicalize(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text:
        return None

    # Prefer alias match on lightly cleaned text first
    light = _NON_ALNUM.sub(" ", text)
    light = re.sub(r"\s+", " ", light).strip()
    for alias, canon in ALIASES:
        if light == alias or light.endswith(" " + alias) or light.startswith(alias + " "):
            return canon
        if f" {alias} " in f" {light} ":
            return canon

    cleaned = _strip_qty_units(text)
    if not cleaned:
        return None

    for alias, canon in ALIASES:
        if cleaned == alias or cleaned.endswith(" " + alias):
            return canon
        if f" {alias} " in f" {cleaned} ":
            return canon

    # Drop trailing form words like "juice", "zest", "breasts"
    for suffix in (" juice", " zest", " breasts", " breast", " sprigs"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
            break

    for alias, canon in ALIASES:
        if cleaned == alias:
            return canon

    # Simple plural trim for obvious cases
    if cleaned.endswith("oes") and len(cleaned) > 4:
        # tomatoes already handled; potatoes → potato via alias
        pass
    elif cleaned.endswith("ies") and len(cleaned) > 4:
        cleaned = cleaned[:-3] + "y"
    elif cleaned.endswith("ses") and len(cleaned) > 4:
        cleaned = cleaned[:-2]
    elif cleaned.endswith("s") and not cleaned.endswith("ss") and len(cleaned) > 3:
        cleaned = cleaned[:-1]

    for alias, canon in ALIASES:
        if cleaned == alias:
            return canon

    return cleaned or None


def normalize_ner(ner: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in ner:
        c = canonicalize(item)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out
