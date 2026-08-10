from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Recipe:
    id: str
    title: str
    ingredients: list[str]
    directions: list[str]
    ner: list[str]
    link: str
    source: str


def _parse_list(raw: str) -> list[str]:
    if raw is None:
        return []
    s = str(raw).strip()
    if not s:
        return []
    try:
        val = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return []
    if not isinstance(val, list):
        return []
    return [str(x) for x in val]


def load_recipes(path: Path | str) -> Iterator[Recipe]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rid = (row.get("") or row.get(None) or str(i)).strip()
            yield Recipe(
                id=rid or str(i),
                title=(row.get("title") or "").strip(),
                ingredients=_parse_list(row.get("ingredients") or ""),
                directions=_parse_list(row.get("directions") or ""),
                ner=_parse_list(row.get("NER") or ""),
                link=(row.get("link") or "").strip(),
                source=(row.get("source") or "").strip(),
            )
