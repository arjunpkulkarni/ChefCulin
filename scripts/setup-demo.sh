#!/usr/bin/env bash
# One-time local demo setup. Large FooDB files stay on disk, not in git.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== ChefCulin local demo setup =="

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env — add VITE_OPENAI_API_KEY for Form / Brainstorm / Associate"
fi

if [[ ! -d pipeline/.venv ]]; then
  echo "Creating pipeline venv…"
  python3 -m venv pipeline/.venv
fi
pipeline/.venv/bin/pip install -q -r pipeline/requirements.txt

CONTENT="pipeline/vendor/foodb/foodb_2020_04_07_csv/Content.csv"
if [[ ! -f "$CONTENT" ]]; then
  echo "Fetching FooDB Content tables (~1GB)…"
  npm run fetch:foodb
else
  echo "FooDB Content.csv present"
fi

if [[ ! -f src/data/balance_axes.json ]]; then
  echo "Building balance artifacts…"
  npm run build:balance
fi

if [[ ! -f pipeline/artifacts/compound/meta.json ]]; then
  echo "Building compound artifacts…"
  npm run build:compound
fi

echo ""
echo "Ready. Run:  npm run demo"
echo "Open:      http://localhost:5173"
echo "API:       http://localhost:8001/health"
