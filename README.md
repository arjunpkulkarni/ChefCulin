# ChefCulin

CulinAI Workspace — a static, client-side prototype, scaffolded on **Vite + React**.

Frontend only: no backend, no live model calls, no persistence. Chat responses
and tradition-thread content are staged/placeholder data.

## Getting started

```bash
npm install
npm run dev      # http://localhost:5173
```

Other scripts:

```bash
npm run build    # production build → dist/
npm run preview  # preview the production build
```

## Project structure

```
index.html          Vite entry (loads src/main.jsx)
src/
  main.jsx          React entry — mounts <App/>
  App.jsx           Thin shell: injects the workspace markup, calls init()
  markup.html       The workspace DOM (imported as a raw string)
  culinai.js        All the app logic (balance/axis, lenses, chat, etc.)
  styles.css        All styling
```

## How it's wired (and why)

The original prototype was a single self-contained `index.html` with inline CSS
and one big imperative `<script>` that drives the UI via `render()` and inline
`onclick="..."` handlers. To scaffold it onto Vite + React without a risky
rewrite, it was split into `styles.css`, `markup.html`, and `culinai.js`:

- `culinai.js` keeps the imperative logic intact. It exposes its handler
  functions on `window` (so the inline `onclick` attributes still resolve) and
  exports an `init()` function instead of auto-running on load.
- `App.jsx` injects `markup.html` via `dangerouslySetInnerHTML`, then calls
  `init()` in a `useEffect` — after the markup is committed to the DOM.
- `main.jsx` intentionally does **not** use `<StrictMode>`, since the imperative
  `init()` should run once against a stable DOM node.

## Board tasks (corpus + Palate Memory)

See [`docs/corpus-and-palate-memory.md`](docs/corpus-and-palate-memory.md) for the two tasks:
RecipeNLG → cooccur/technique artifacts, and the Postgres Palate Memory store.

## Pipeline (Lens 3 + technique layer)

See [`pipeline/README.md`](pipeline/README.md). Acceptance tests drive the ETL:

```bash
cd pipeline && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" && pytest -q
```

Artifacts: ingredient co-occurrence (NPMI) and ingredient→technique frequencies.
The 2.1GB RecipeNLG CSV in `src/full_dataset.csv` is gitignored — use the mini
fixture under `pipeline/tests/fixtures/` for development.

## Future work

Componentize incrementally — replace the `dangerouslySetInnerHTML` + `init()`
bridge with real React components and state, one lens/pane at a time (Compound,
Tradition, Co-occurrence, Form, Brainstorm). The logic in `culinai.js` (`AXES`,
`FRAMES`, `dishRead()`, `balance()`, `applyOverlays()`, `tensionFor()`, cuisine
lock, form carve-out) is the design intent to preserve as you migrate.
