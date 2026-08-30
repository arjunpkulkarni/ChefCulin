#!/usr/bin/env python3
"""Download and extract FooDB CSV tables needed for balance-axis content wiring."""
from __future__ import annotations

import sys
import tarfile
import urllib.request
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))

from culin_etl.vendor_paths import FOODB_CSV_DIR, FOODB_ROOT  # noqa: E402

FOODB_CSV_URL = "https://foodb.ca/public/system/downloads/foodb_2020_4_7_csv.tar.gz"
NEEDED = (
    "foodb_2020_04_07_csv/Content.csv",
    "foodb_2020_04_07_csv/Compound.csv",
    "foodb_2020_04_07_csv/Nutrient.csv",
    "foodb_2020_04_07_csv/Food.csv",
)


def main() -> None:
    FOODB_ROOT.mkdir(parents=True, exist_ok=True)
    archive = FOODB_ROOT / "foodb_csv.tar.gz"
    if not archive.exists():
        print(f"Downloading FooDB CSV bundle → {archive}")
        urllib.request.urlretrieve(FOODB_CSV_URL, archive)
    else:
        print(f"Using cached archive {archive}")

    print("Extracting Content, Compound, Nutrient, Food …")
    with tarfile.open(archive, "r:gz") as tar:
        members = [m for m in tar.getmembers() if m.name in NEEDED]
        tar.extractall(path=FOODB_ROOT.parent, members=members)

    missing = [p for p in (
        FOODB_CSV_DIR / "Content.csv",
        FOODB_CSV_DIR / "Compound.csv",
        FOODB_CSV_DIR / "Nutrient.csv",
        FOODB_CSV_DIR / "Food.csv",
    ) if not p.exists()]
    if missing:
        raise SystemExit(f"Missing after extract: {missing}")

    print(f"FooDB CSV ready under {FOODB_CSV_DIR}")


if __name__ == "__main__":
    main()
