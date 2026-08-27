#!/usr/bin/env python3
"""
Build compound-neighbor artifacts from vendored flavor-network edge CSV (no NetworkX).

Default source: pipeline/vendor/flavor_network/ingredient_filtered_named_edges.csv
Output: pipeline/artifacts/compound/neighbors.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline"
DEFAULT_OUT = PIPELINE / "artifacts" / "compound"
sys.path.insert(0, str(PIPELINE))

from culin_etl.compound_network import display_name, is_same_base  # noqa: E402
from culin_etl.vendor_paths import EDGES_CSV  # noqa: E402

DEFAULT_CSV = EDGES_CSV


def build(csv_path: Path, out_dir: Path, *, per_seed: int = 32, min_weight: int = 2) -> dict:
    print(f"Loading {csv_path}...", flush=True)
    adj: dict[str, list[tuple[str, int]]] = defaultdict(list)
    weights: list[int] = []

    with csv_path.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            a, b, w = row[0].strip(), row[1].strip(), int(row[2])
            weights.append(w)
            adj[a].append((b, w))
            adj[b].append((a, w))

    w_min, w_max = min(weights), max(weights)
    span = w_max - w_min or 1

    rows = []
    for seed, pairs in adj.items():
        pairs.sort(key=lambda x: -x[1])
        kept = 0
        for nb, w in pairs:
            if w < min_weight:
                continue
            if is_same_base(seed, nb):
                continue
            conf = round((w - w_min) / span, 4)
            rows.append(
                {
                    "seed": seed,
                    "neighbor": nb,
                    "display": display_name(nb),
                    "weight": w,
                    "confidence": conf,
                }
            )
            kept += 1
            if kept >= per_seed:
                break

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "neighbors.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    meta = {
        "source": str(csv_path.resolve()),
        "seeds": len(adj),
        "neighbor_rows": len(rows),
        "weight_min": w_min,
        "weight_max": w_max,
        "per_seed": per_seed,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows → {out_path}", flush=True)
    return meta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build flavor-compound neighbor artifacts")
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--per-seed", type=int, default=32)
    p.add_argument("--min-weight", type=int, default=2)
    args = p.parse_args(argv)

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 1

    build(args.csv, args.out, per_seed=args.per_seed, min_weight=args.min_weight)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
