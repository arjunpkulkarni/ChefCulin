# ChefCulin

CulinAI Workspace — Vite + React frontend, FastAPI artifact/palate backend.

## Send the demo to founders

GitHub cannot host the full FooDB dataset (~1.8 GB). **Bundle the project folder** and send it directly.

```bash
npm run pack:demo
```

Creates `dist/chefculin-demo-YYYYMMDD.zip` (~1–2 GB) with all vendor data, artifacts, and code. **Too large to email as an attachment** — upload to Google Drive, Dropbox, or WeTransfer and send the link plus `FOUNDERS.md`.

Founders unzip and follow **[FOUNDERS.md](FOUNDERS.md)** — about 5 minutes to `npm run demo`.

The zip includes `.env` with the demo OpenAI key (founder handoff only — do not commit or publish the zip).

---

## Local demo (your machine)

The demo runs entirely on your machine. **You do not need to push large FooDB files to GitHub** — keep them local or fetch once after clone.

**You already have the data on this machine** if `pipeline/vendor/foodb/.../Content.csv` exists (~744MB). Git only needs the code + small tables.

```bash
cp .env.example .env          # add VITE_OPENAI_API_KEY
npm install
npm run setup:demo            # venv, FooDB if missing, build artifacts
npm run demo                  # API :8001 + Vite :5173
```

Open **http://localhost:5173**. Compound, Tradition, Co-occurrence, Balance, and Associate work offline; Form / Brainstorm need the OpenAI key in `.env`.

Optional — Palate Save (F6) needs Postgres:

```bash
cd pipeline && docker compose up -d
# restart npm run demo if Postgres was started after the API
```

### What stays local (not on GitHub)

| File | Size | How to get it |
|------|------|----------------|
| `Content.csv` | ~744 MB | `npm run fetch:foodb` |
| `foodb_csv.tar.gz` | ~953 MB | same script (cached) |

Smaller FooDB tables (`Food.csv`, `Compound.csv`, `Nutrient.csv`), `balance_axes.json`, and `pipeline/artifacts/` **are** in git when committed.

### Hand off without the zip

Clone from GitHub + `npm run setup:demo` downloads FooDB (~1 GB) on first run. Slower but works if you only push code.

---

## Getting started (quick)

```bash
cp .env.example .env   # add VITE_OPENAI_API_KEY for Form / Brainstorm
npm install
npm run demo           # API :8001 + Vite :5173 (one command)
```

Optional — Palate Save needs Postgres:

```bash
cd pipeline && docker compose up -d
export DATABASE_URL=postgresql://culin:culin@127.0.0.1:5432/culin
# restart npm run demo if Postgres was started after the API
```

Run frontend or API alone:

```bash
npm run dev            # :5173 (proxies /api → :8001)
npm run api            # corpus + compound artifacts
```

Vite proxies `/api/*` to FastAPI. Co-occurrence lens loads live neighbors from `GET /cooccur`.

```bash
npm run build
npm run preview
npm test              # vitest
```

`npm test` includes an end-to-end suite that drives the real app against a running
backend and **skips itself** when nothing is listening on `:8001`, so it is green
either way. Point it elsewhere with `CULIN_API=http://host:port npm test`.

> The API binds its Postgres store at startup. If you start Postgres *after*
> `culin_etl.serve`, restart the API or `/palate` stays 503 and `palate_db` stays
> `false`.

## What runs where

| Feature | Frontend | Backend |
|---------|----------|---------|
| Compound / Tradition lenses | static tables in `src/data/` | — |
| Co-occurrence lens | `CooccurPane` | `GET /cooccur`, `GET /techniques` (precomputed NPMI artifacts) |
| **Associate** (D1/D2) | `AssociationPanel` + `src/lib/associationEngine.js` | reuses `GET /cooccur` |
| **Balance / trending** (E4/E5) | `src/lib/balance.js`, `DishSidebar` | none — dish-local math |
| **F6 Save / Discard** | `DishSidebar` → `saveDish` | `POST /palate` → Postgres |

Only F6 Save writes anything. Everything else is read-only or session state.

## Project structure

```
src/
  App.jsx                 React workspace root
  main.jsx
  api.js                  FastAPI client
  styles.css
  context/WorkspaceContext.jsx
  components/             Mast, DishSidebar, lenses, chips…
  data/                   domain tables + lens content (JS modules)
  lib/                    balance/trending, association engine, chat, user id
pipeline/                 ETL + Postgres palate + API
docs/
```

No `markup.html` / `dangerouslySetInnerHTML` bridge — the UI is React components.

## Lenses

Compound, Tradition and Co-occurrence are separate tabs and stay that way. The
**Associate** tab asks all three at once and shows where they converge and where
they pull apart — it merges the lenses, it does not replace them.

## Session vs. memory

Trending flags and the chef's Accept / Adjust / Override on them live in
`WorkspaceContext.balanceDecisions` — **session state, never written anywhere**.
Association results are not persisted at all. Palate Memory is written by **F6 Save
only** (`POST /palate`), and its snapshot deliberately excludes the balance decisions.
Working decisions are not a committed dish; don't conflate the two.

## Board tasks

- [`docs/association-engine.md`](docs/association-engine.md) — D1 cross-lens
  orchestration, D2 disagreement handling
- [`docs/trending-detection.md`](docs/trending-detection.md) — E4 flag + corrective
  pair, E5 session decision capture
- [`docs/corpus-and-palate-memory.md`](docs/corpus-and-palate-memory.md) — corpus
  artifacts, Palate Memory
