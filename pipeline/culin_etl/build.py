from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional

from culin_etl.cooccur import accumulate_cooccur, finalize_cooccurrence
from culin_etl.diet import tag_recipe
from culin_etl.normalize import normalize_ner
from culin_etl.parse import load_recipes
from culin_etl.quality import is_low_quality
from culin_etl.techniques import TechniqueAccumulator


def _fingerprint(ings: list[str], directions: list[str]) -> str:
    ner = "|".join(sorted(ings))
    dirs = "||".join(d.strip().lower() for d in directions)
    return hashlib.md5(f"{ner}::{dirs}".encode("utf-8")).hexdigest()


def build_artifacts(
    path: Path | str,
    *,
    limit: Optional[int] = None,
    min_pair_freq: int = 1,
    min_tech_freq: int = 1,
    keep_recipes: bool = True,
    progress_every: int = 0,
) -> dict:
    """
    Parse → filter → normalize → cooccur + technique tables.

    Streaming-friendly: does not require loading the full corpus into a list of
    Recipe objects first. Set keep_recipes=False for large corpus builds.
    """
    path = Path(path)
    seen_fp: set[str] = set()
    recipe_rows: list[dict] = []
    ing_lists: list[list[str]] = []

    doc_freq: Counter = Counter()
    pair_freq: Counter = Counter()
    n_cooccur = 0
    tech_acc = TechniqueAccumulator()

    scanned = kept = dumped = 0
    t0 = time.time()

    for r in load_recipes(path):
        scanned += 1
        if limit is not None and kept >= limit:
            break
        if is_low_quality(r):
            dumped += 1
            continue

        ings = normalize_ner(r.ner) if r.ner else normalize_ner(r.ingredients)
        if len(ings) < 2:
            dumped += 1
            continue

        fp = _fingerprint(ings, list(r.directions))
        if fp in seen_fp:
            dumped += 1
            continue
        seen_fp.add(fp)

        dirs = list(r.directions)
        tags = tag_recipe(ings)
        row = {
            "id": r.id,
            "title": r.title,
            "ingredients": ings,
            "directions": dirs,
            "link": r.link,
            "source": r.source,
            **tags,
        }
        kept += 1

        if keep_recipes:
            recipe_rows.append(row)
        else:
            ing_lists.append(ings)

        _, _, dn = accumulate_cooccur([ings], doc_freq, pair_freq)
        n_cooccur += dn
        tech_acc.add(ings, dirs)

        if progress_every and scanned % progress_every == 0:
            elapsed = time.time() - t0
            rate = scanned / elapsed if elapsed else 0
            print(
                f"  scanned={scanned:,} kept={kept:,} dumped={dumped:,} "
                f"pairs={len(pair_freq):,} ({rate:,.0f} recipes/s)",
                file=sys.stderr,
                flush=True,
            )

    cooccur = finalize_cooccurrence(
        doc_freq, pair_freq, n_cooccur, min_freq=min_pair_freq
    )
    ingredient_technique = tech_acc.finalize(min_freq=min_tech_freq)

    return {
        "recipes": recipe_rows if keep_recipes else [],
        "cooccur": cooccur,
        "ingredient_technique": ingredient_technique,
        "meta": {
            "source": str(path.resolve()),
            "scanned": scanned,
            "kept": kept,
            "dumped": dumped,
            "cooccur_recipes": n_cooccur,
            "cooccur_edges": len(cooccur),
            "technique_edges": len(ingredient_technique),
            "unique_ingredients": len(doc_freq),
            "min_pair_freq": min_pair_freq,
            "min_tech_freq": min_tech_freq,
            "seconds": round(time.time() - t0, 2),
        },
    }


def write_artifacts(artifacts: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = artifacts.get("meta", {})
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    with (out_dir / "cooccur.jsonl").open("w", encoding="utf-8") as f:
        for row in artifacts["cooccur"]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with (out_dir / "ingredient_technique.jsonl").open("w", encoding="utf-8") as f:
        for row in artifacts["ingredient_technique"]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Optional: keep recipes only when small (tests / samples)
    if artifacts.get("recipes"):
        with (out_dir / "recipes.jsonl").open("w", encoding="utf-8") as f:
            for row in artifacts["recipes"]:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_artifact_tables(out_dir: Path) -> dict:
    """Reload cooccur + technique tables from a prior write_artifacts() run."""
    def _load(name: str) -> list[dict]:
        path = out_dir / name
        if not path.exists():
            return []
        rows = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    return {
        "cooccur": _load("cooccur.jsonl"),
        "ingredient_technique": _load("ingredient_technique.jsonl"),
        "recipes": _load("recipes.jsonl"),
        "meta": meta,
    }


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    default_input = repo_root / "src" / "full_dataset.csv"
    default_out = Path(__file__).resolve().parents[1] / "artifacts" / "corpus"

    p = argparse.ArgumentParser(description="Build CulinAI cooccur + technique artifacts")
    p.add_argument("--input", type=Path, default=default_input, help="RecipeNLG CSV path")
    p.add_argument("--out", type=Path, default=default_out, help="Output directory")
    p.add_argument("--limit", type=int, default=None, help="Max kept recipes (smoke test)")
    p.add_argument("--min-pair-freq", type=int, default=5, help="Drop rare cooccur edges")
    p.add_argument("--min-tech-freq", type=int, default=3, help="Drop rare technique edges")
    p.add_argument(
        "--keep-recipes",
        action="store_true",
        help="Also write recipes.jsonl (memory-heavy on full corpus)",
    )
    p.add_argument("--progress-every", type=int, default=50_000)
    args = p.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    print(f"Building from {args.input} ({args.input.stat().st_size / 1e9:.2f} GB)", flush=True)
    arts = build_artifacts(
        args.input,
        limit=args.limit,
        min_pair_freq=args.min_pair_freq,
        min_tech_freq=args.min_tech_freq,
        keep_recipes=args.keep_recipes,
        progress_every=args.progress_every,
    )
    write_artifacts(arts, args.out)
    print(json.dumps(arts["meta"], indent=2), flush=True)
    print(f"Wrote artifacts → {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
