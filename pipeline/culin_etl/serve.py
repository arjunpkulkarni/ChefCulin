from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from culin_etl.api import DEFAULT_ARTIFACTS, create_app


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Serve CulinAI artifact API")
    p.add_argument(
        "--artifacts",
        type=Path,
        default=Path(
            __import__("os").environ.get("CULIN_ARTIFACTS", DEFAULT_ARTIFACTS)
        ),
        help="Directory with cooccur.jsonl + ingredient_technique.jsonl",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)

    app = create_app(artifacts_dir=args.artifacts)
    print(f"Serving {args.artifacts} on http://{args.host}:{args.port}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
