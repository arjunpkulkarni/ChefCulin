# ChefCulin

CulinAI Workspace — Vite + React frontend, FastAPI artifact/palate backend.

## Getting started

```bash
# backend (corpus + palate)
cd pipeline && docker compose up -d
export DATABASE_URL=postgresql://culin:culin@127.0.0.1:5432/culin
python -m culin_etl.serve          # :8000

# frontend (proxies /api → :8000)
cd .. && npm install && npm run dev   # :5173
```

Vite proxies `/api/*` to FastAPI. Co-occurrence lens loads live neighbors from `GET /cooccur`.

```bash
npm run build
npm run preview
```

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
  lib/                    balance, chat helpers
pipeline/                 ETL + Postgres palate + API
docs/corpus-and-palate-memory.md
```

No `markup.html` / `dangerouslySetInnerHTML` bridge — the UI is React components.

## Board tasks

See [`docs/corpus-and-palate-memory.md`](docs/corpus-and-palate-memory.md).
