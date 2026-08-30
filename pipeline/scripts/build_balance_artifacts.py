#!/usr/bin/env python3
"""Build balance-axis artifacts from FooDB compound assignments → src/data/balance_axes.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))

from culin_etl.balance_axes import build_foodb_balance_rows  # noqa: E402

ROOT = PIPELINE.parent
OUT_JSON = ROOT / "src" / "data" / "balance_axes.json"
OUT_ARTIFACT = PIPELINE / "artifacts" / "balance" / "axes.jsonl"


def main() -> None:
    rows, meta = build_foodb_balance_rows()
    payload = {"meta": meta, "rows": rows}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    OUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ARTIFACT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    meta_path = OUT_ARTIFACT.parent / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(
        f"Wrote {len(rows)} balance profiles → {OUT_JSON.relative_to(ROOT)} "
        f"({meta['compound_backed']} compound-backed, {meta.get('content_backed', 0)} content-backed)"
    )


if __name__ == "__main__":
    main()
