# CulinAI ETL — co-occurrence + technique artifacts

Worked **backward from acceptance tests**. The mini fixture encodes expected truths; the pipeline exists to make those tests green.

## Quick start

```bash
cd pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## What the tests lock in

| Test file | Acceptance |
|-----------|------------|
| `test_normalize.py` | tomato / potato / chicken variants collapse |
| `test_cooccur.py` | `duck` → orange/butter/thyme; not sprinkles; NPMI + freq; sorted |
| `test_techniques.py` | controlled vocab; duck → sear/roast; short ribs → braise |
| `test_quality.py` | junk filtered; near-dupe doesn’t inflate freq |
| `test_api.py` | `GET /cooccur`, `GET /techniques` |

Fixture: `tests/fixtures/mini_recipes.csv` (hand-authored, not the 2.1GB corpus).

## Algos in play

- Canonicalize: alias map + qty/unit strip + light plural trim  
- Co-occur: pair counts + **NPMI** confidence  
- Techniques: regex lexicon over steps → `(ingredient, technique)` with **P(tech\|ing)**  
- Quality: empty/thin filter + exact NER+directions fingerprint dedupe  

## Serve artifacts (Lens 3 + technique lookups)

**Why an API:** the corpus build already did the heavy work. The app should hit
precomputed edge tables (`artifacts/corpus/`), not rescanning 2.1GB of recipes
per chef click. FastAPI is just a thin indexed top-N read over those files.

```bash
# serves pipeline/artifacts/corpus by default
python -m culin_etl.serve
# or: uvicorn culin_etl.api:app_factory --factory --port 8000
```

Endpoints:
- `GET /health` — edge counts + artifact path
- `GET /meta` — build stats from `meta.json`
- `GET /cooccur?ingredient=duck&n=10`
- `GET /techniques?ingredient=garlic&n=10`

Override path: `CULIN_ARTIFACTS=artifacts/smoke python -m culin_etl.serve`

## Palate Memory (local Postgres)

MVP memory store for F6 Save/Discard — **not** personalization.

```bash
# start Postgres
docker compose up -d

# schema loads from sql/001_palate.sql on first boot
export DATABASE_URL=postgresql://culin:culin@127.0.0.1:5432/culin

pytest tests/test_palate.py -q
python -m culin_etl.serve
```

| Method | Path | Meaning |
|--------|------|---------|
| `POST` | `/palate` | F6 **Save** — write snapshot |
| `GET` | `/palate?user_id=` | list that user's memories |
| `GET` | `/palate/{id}` | fetch one |
| `DELETE` | `/palate/{id}?user_id=` | remove a saved memory |

**Discard** = do not `POST`. No row is written.

## Full corpus build

```bash
# smoke (5k kept recipes)
python -m culin_etl.build --limit 5000 --out artifacts/smoke

# full RecipeNLG CSV (~2.1GB) → artifacts/corpus/
python -m culin_etl.build \
  --input ../src/full_dataset.csv \
  --out artifacts/corpus \
  --min-pair-freq 5 \
  --min-tech-freq 3
```

Writes:
- `cooccur.jsonl` — `{a,b,freq,confidence}` (NPMI)
- `ingredient_technique.jsonl` — `{ingredient,technique,freq,confidence}`
- `meta.json` — scan stats + timing

Defaults drop rare edges (`min-pair-freq=5`, `min-tech-freq=3`) so the full-corpus tables stay lookup-sized. Fixture tests still use `min_*=1` via `build_artifacts(path)`.
