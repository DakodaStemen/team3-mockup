#!/usr/bin/env bash
# Start the backend (http://localhost:8000) and frontend (http://localhost:5173) together. Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || { echo "Install uv first: https://docs.astral.sh/uv/"; exit 1; }
command -v npm >/dev/null || { echo "Install Node.js 22+ first"; exit 1; }
(cd backend && uv sync --quiet)
[ -d frontend/node_modules ] || (cd frontend && npm ci --silent)
trap 'kill 0' EXIT INT TERM
(cd backend && uv run uvicorn planner.api:app --port 8000 --reload) &
(cd frontend && npm run dev -- --port 5173 --strictPort) &
echo "Open http://localhost:5173  (API docs: http://localhost:8000/docs)"
wait
