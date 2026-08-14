# Board tasks: Corpus artifacts + Palate Memory

Two separate systems. Do not conflate them.

| Task | Job | Personalization? |
|------|-----|------------------|
| **1. Corpus artifacts** | Offline RecipeNLG → co-occurrence + technique tables (Lens 3 / technique layer) | No |
| **2. Palate Memory** | Persist F6 Save/Discard decisions (per-user) | No (MVP is storage only; adaptive layer deferred) |

---

## 1. Corpus artifacts (Lens 3 + technique layer)

### Objective

Turn the raw RecipeNLG corpus into two **precomputed** artifacts:

1. **Ingredient co-occurrence** — powers Lens 3  
2. **Ingredient → technique** — powers the technique layer (regional join from Lens 2 later)

Not computed live over the CSV at request time.

### Corpus

- Source: [RecipeNLG on Kaggle](https://www.kaggle.com/datasets/saldenisov/recipenlg) (confirm license before commercial use)
- Local file: `src/full_dataset.csv` (~2.1GB, ~2.23M rows, **gitignored**)
- Schema: `title`, `ingredients` (raw lines), `directions` (steps), `link`, `source`, `NER` (pre-extracted names)

### Algos

| Step | Approach |
|------|----------|
| Normalize | Alias map + strip qty/units + light plurals |
| Co-occurrence | Pair counts + **NPMI** confidence |
| Techniques | Controlled vocab + regex over steps → `(ingredient, technique)` with **P(tech\|ing)** |
| Quality | Drop empty/thin recipes; dedupe identical NER+directions fingerprints |
| Diet/allergens | Dictionary tags (enrichment; not the hot path) |

**Out of scope here:** embeddings, live LLM extraction, graph DB, adaptive ranking.

### Build

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# smoke
python -m culin_etl.build --limit 5000 --out artifacts/smoke

# full corpus
python -m culin_etl.build \
  --input ../src/full_dataset.csv \
  --out artifacts/corpus \
  --min-pair-freq 5 \
  --min-tech-freq 3
```

Outputs in `pipeline/artifacts/corpus/`:

- `cooccur.jsonl` — `{a, b, freq, confidence}`
- `ingredient_technique.jsonl` — `{ingredient, technique, freq, confidence}`
- `meta.json` — scan stats

Last full run (approx): **2.22M kept** recipes → **~600k** cooccur edges, **~81k** technique edges, **~20 min**.

### Serve (lookups)

```bash
python -m culin_etl.serve
# GET /cooccur?ingredient=garlic&n=10
# GET /techniques?ingredient=duck&n=10
# GET /health  GET /meta
```

Why an API: the chef UI should hit **indexed top-N over edge tables**, never rescanning 2.1GB.

### Tests (work backward from acceptance)

Fixture: `pipeline/tests/fixtures/mini_recipes.csv`

| Test | Locks |
|------|--------|
| `test_normalize.py` | tomato/potato/chicken variants collapse |
| `test_cooccur.py` | duck → orange/butter/thyme; not sprinkles; sorted NPMI |
| `test_techniques.py` | vocab; duck → sear/roast; short ribs → braise |
| `test_quality.py` | junk filtered; near-dupe doesn’t inflate freq |
| `test_api.py` | HTTP top-N shape |

```bash
cd pipeline && pytest -q
```

### Graph DB?

**Not for this task.** One-hop neighbors are fine as Postgres/JSONL edge tables. Revisit a graph store only for multi-hop traversals (e.g. duck → cooccur → roast-associated → also with orange → 2nd hop), which are not in current Lens 3 scope.

---

## 2. Palate Memory (local Postgres)

### Objective

**G1** — Data model + storage decision (what is persisted; **per-user**).  
**G2** — Wire F6 Save/Discard to real storage.  
**G3** — Adaptive threshold read-path — **explicitly deferred**. Do not build personalization/adaptivity here.

### Why

Without this, F6 Save/Discard has nowhere to land (UI claim, no persistence). Palate Memory is the **memory store** that later personalization can read — it is not that engine yet.

### What gets stored

Snapshot of a committed decision, not the chat log:

```text
user_id, dish[], form, cuisine_scope, source ("f6"), created_at
```

### Stack

| Piece | Choice |
|-------|--------|
| DB | Local **Postgres 16** (Docker Compose) |
| Access | Same FastAPI app as artifacts |
| Scope | **Per-user** |

No graph DB. No SQLite once Postgres is the chosen local store.

### Run

```bash
cd pipeline
docker compose up -d          # needs Colima/Docker running
export DATABASE_URL=postgresql://culin:culin@127.0.0.1:5432/culin
python -m culin_etl.serve
```

Schema: `pipeline/sql/001_palate.sql` → table `palate_memories`.

### API

| Method | Path | Meaning |
|--------|------|---------|
| `POST` | `/palate` | **Save** — write a row |
| `GET` | `/palate?user_id=` | list that user’s memories |
| `GET` | `/palate/{id}` | fetch one |
| `DELETE` | `/palate/{id}?user_id=` | remove a saved memory |

**Discard** = do not `POST`. No row is written (`PalateStore.discard()` is an explicit no-op).

**F6 Save is the only writer.** The balance decisions a chef makes while composing
(E4/E5 Accept / Adjust / Override) stay in `WorkspaceContext.balanceDecisions` and
never reach this table — see [`trending-detection.md`](trending-detection.md). The
Association Engine (D1/D2) writes nothing at all — see
[`association-engine.md`](association-engine.md).

### Tests

`pipeline/tests/test_palate.py` (skipped if Postgres is down):

- Save writes a record  
- Discard writes nothing  
- Per-user isolation  
- Round-trip get  
- API save + list  

```bash
docker compose up -d
export DATABASE_URL=postgresql://culin:culin@127.0.0.1:5432/culin
pytest tests/test_palate.py -q
```

Frontend side, `npm test`:

- `src/context/PalateSave.test.jsx` — Save posts `source: 'f6'`, Discard posts
  nothing, editing re-arms, a 503 surfaces instead of failing silently, and balance
  decisions never appear in the payload
- `src/lib/liveApi.test.jsx` — the real app against the real backend: gather a dish,
  read the trend, merge three lenses, Save, and read the row back out of Postgres.
  Skips itself when the API is not running

> **Note:** the API binds its Postgres store once at startup. Starting Postgres
> *after* `culin_etl.serve` leaves `palate_db: false` until the API is restarted.

---

## How they relate

```text
RecipeNLG CSV ──ETL──► cooccur + technique artifacts ──API──► Lens 3 / techniques
                                                              (global, precomputed)

F6 Save ──POST /palate──► Postgres palate_memories ──► later: adaptive/personalization (G3)
F6 Discard ──(no write)──► nothing
                                                              (per-user, session decisions)
```

Corpus artifacts = **shared culinary evidence**.  
Palate Memory = **this chef’s kept decisions**.  
Different tables, different jobs; both served from `python -m culin_etl.serve` when Postgres and `artifacts/corpus` are available.

---

## Frontend wiring (React)

The workspace is **React only** (`WorkspaceProvider` + lens components). No HTML shell.

Vite proxies `/api/*` → FastAPI (`vite.config.js`). Client: `src/api.js`.

`CooccurPane` loads live neighbors when the dish changes:

- `GET /api/cooccur?ingredient=<seed>&n=24` — seed = last dish ingredient, else `duck`
- `GET /api/techniques?ingredient=<seed>&n=8`
- Hub ingredients (salt, butter, …) filtered client-side via `HUBS`, exported from
  `src/lib/associationEngine.js` so the pane and the merged view cannot drift apart

Staged Fat reset / carrier / depth groups remain as design framing below the live block.

### F6 Save / Discard — the only write in the app

Lives at the bottom of `DishSidebar` ("Keep this dish"); the logic is `saveDish` /
`discardDish` in `WorkspaceContext`.

| Action | What happens |
|--------|--------------|
| **Save** | `POST /palate` with `{ user_id, dish, form, cuisine_scope, source: 'f6' }` |
| **Discard** | **Nothing.** No request is made, mirroring `PalateStore.discard()` |

What the snapshot carries: ingredient names, their lens and their committed form;
the frame; the cuisine scope. **Balance decisions (E5) are deliberately excluded** —
persisting them is out of scope for that board, and the panel says so on screen
rather than leaving the boundary invisible.

**Identity.** There is no auth, so `src/lib/user.js` mints a `chef-<uuid>` on first
use and keeps it in `localStorage`. Enough to keep one browser's kept dishes
separate from another's, and honest about being nothing more. It falls back to a
shared `chef-local` where storage is blocked, because losing per-browser separation
beats losing Save entirely.

**Re-arming.** Save is answered against a signature of the plate (ingredients,
forms, frame, scope). Edit anything and the button re-arms rather than leaving a
stale "Saved" badge over a dish that has since changed.

**When Postgres is down** the API returns 503 and the sidebar says so, with the
command to fix it. The rest of the workspace — every lens, the balance read, the
Association Engine — keeps working; only Save is unavailable.
