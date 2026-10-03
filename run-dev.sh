#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
trap 'kill 0' EXIT INT TERM

if [[ -x "$ROOT/backend/.venv/bin/python" ]]; then
  PYTHON="$ROOT/backend/.venv/bin/python"
elif [[ -x "$ROOT/.python/bin/python" ]]; then
  PYTHON="$ROOT/.python/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

(cd "$ROOT/backend" && USE_MOCK_AI=true "$PYTHON" -m uvicorn main:app --reload --port 8000) &
(cd "$ROOT/frontend" && npm run dev) &
wait
