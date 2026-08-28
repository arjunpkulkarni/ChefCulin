"""
Parse FooDB Content.csv for nutrition-grade balance axis values (mg/100g).

Uses explicit compound / nutrient name matches to avoid peptide false positives.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, Optional, Set, Tuple

from culin_etl.vendor_paths import (
    FOODB_COMPOUND_CSV,
    FOODB_CONTENT_CSV,
    FOODB_NUTRIENT_CSV,
)

AXES = (
    "glut",
    "nucl",
    "salt",
    "fat",
    "acid",
    "sweet",
    "capsaicin",
    "pungent",
    "trigeminal",
)

# Exact compound names (case-insensitive) → axis. Sweet compounds are summed.
CONTENT_COMPOUND_EXACT: Dict[str, str] = {}
for names, axis in [
    (("L-Glutamic acid", "Glutamic acid"), "glut"),
    (("Sodium",), "salt"),
    (
        (
            "Sucrose",
            "D-Fructose",
            "D-Glucose",
            "Fructose",
            "Glucose",
            "Maltose",
            "Lactose",
            "Galactose",
        ),
        "sweet",
    ),
    (
        (
            "Citric acid",
            "L-Malic acid",
            "Malic acid",
            "Acetic acid",
            "Lactic acid",
            "D-Lactic acid",
            "L-Lactic acid",
            "Tartaric acid",
            "Fumaric acid",
            "Succinic acid",
        ),
        "acid",
    ),
    (
        (
            "Disodium inosinate",
            "Disodium guanylate",
            "Inosine 5'-monophosphate",
            "Guanosine 5'-monophosphate",
            "5'-Inosinic acid",
            "5'-Guanylic acid",
        ),
        "nucl",
    ),
    (("Capsaicin", "Dihydrocapsaicin", "Nordihydrocapsaicin"), "capsaicin"),
    (
        (
            "Allyl isothiocyanate",
            "Phenethyl isothiocyanate",
            "Sinigrin",
        ),
        "pungent",
    ),
    (("Piperine", "Gingerol", "6-Shogaol", "Eugenol"), "trigeminal"),
]:
    for name in names:
        CONTENT_COMPOUND_EXACT[name.lower()] = axis

# Nutrient.csv names → axis (FooDB macro nutrients).
CONTENT_NUTRIENT_EXACT: Dict[str, str] = {
    "fat": "fat",
}

RAW_PREP = re.compile(r"\braw\b", re.I)


def _parse_mg(value: str) -> Optional[float]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        v = float(text)
    except ValueError:
        return None
    return v if v > 0 else None


def load_compound_id_axes(path: Path = FOODB_COMPOUND_CSV) -> Dict[str, str]:
    """compound_id → axis for content-backed analytes."""
    out: Dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            axis = CONTENT_COMPOUND_EXACT.get(row["name"].strip().lower())
            if axis:
                out[row["id"]] = axis
    return out


def load_nutrient_id_axes(path: Path = FOODB_NUTRIENT_CSV) -> Dict[str, str]:
    out: Dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            axis = CONTENT_NUTRIENT_EXACT.get(row["name"].strip().lower())
            if axis:
                out[row["id"]] = axis
    return out


def _prep_bucket(preparation_type: str) -> str:
    prep = str(preparation_type or "").strip().lower()
    if not prep:
        return "unspecified"
    if RAW_PREP.search(prep):
        return "raw"
    return "other"


def _aggregate_source_values(
    buckets: Dict[Tuple[str, str, str], list],
    compound_axes: Dict[str, str],
    nutrient_axes: Dict[str, str],
) -> Dict[str, Dict[str, float]]:
    """
  buckets: (food_id, source_type, source_id) → list of (prep_bucket, mg/100g)
  Returns food_id → axis → mg/100g.
  """
    per_food_axis: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for (food_id, source_type, source_id), readings in buckets.items():
        if source_type == "Compound":
            axis = compound_axes.get(source_id)
        elif source_type == "Nutrient":
            axis = nutrient_axes.get(source_id)
        else:
            continue
        if not axis:
            continue

        by_prep: Dict[str, list] = defaultdict(list)
        for prep_bucket, mg in readings:
            by_prep[prep_bucket].append(mg)

        chosen: list[float] = []
        if by_prep.get("raw"):
            chosen = by_prep["raw"]
        elif by_prep.get("unspecified"):
            chosen = by_prep["unspecified"]
        else:
            for vals in by_prep.values():
                chosen.extend(vals)

        if not chosen:
            continue
        per_food_axis[food_id][axis].append(median(chosen))

    out: Dict[str, Dict[str, float]] = {}
    for food_id, axis_lists in per_food_axis.items():
        axes: Dict[str, float] = {}
        for axis, vals in axis_lists.items():
            if axis == "sweet":
                axes[axis] = sum(vals)
            else:
                axes[axis] = max(vals)
        out[food_id] = axes
    return out


def load_content_profiles(
    target_food_ids: Iterable[str],
    content_path: Path = FOODB_CONTENT_CSV,
    compound_path: Path = FOODB_COMPOUND_CSV,
    nutrient_path: Path = FOODB_NUTRIENT_CSV,
) -> Tuple[Dict[str, Dict[str, float]], dict]:
    """
    Stream Content.csv and return food_id → raw axis totals (mg/100g).

    Only rows for target_food_ids are retained.
    """
    targets: Set[str] = {str(fid) for fid in target_food_ids}
    if not targets:
        return {}, {"content_rows_scanned": 0, "content_foods": 0}

    compound_axes = load_compound_id_axes(compound_path)
    nutrient_axes = load_nutrient_id_axes(nutrient_path)

    buckets: Dict[Tuple[str, str, str], list] = defaultdict(list)
    scanned = 0

    with content_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scanned += 1
            food_id = str(row.get("food_id") or "")
            if food_id not in targets:
                continue
            mg = _parse_mg(row.get("standard_content") or "")
            if mg is None:
                continue
            source_type = row.get("source_type") or ""
            source_id = str(row.get("source_id") or "")
            prep = _prep_bucket(row.get("preparation_type") or "")
            buckets[(food_id, source_type, source_id)].append((prep, mg))

    profiles = _aggregate_source_values(buckets, compound_axes, nutrient_axes)
    hits = sum(1 for axes in profiles.values() if axes)
    return profiles, {
        "content_rows_scanned": scanned,
        "content_foods": hits,
        "content_csv": str(content_path.resolve()),
    }
