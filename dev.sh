#!/usr/bin/env bash
# Start the backend (http://localhost:8000) and frontend (http://localhost:5173) together. Ctrl+C stops both.
# Works with macOS's bash 3.2 and Linux bash.
set -euo pipefail
cd "$(dirname "$0")"

die() { echo "dev.sh: $*" >&2; exit 1; }
command -v uv >/dev/null || die "install uv first: https://docs.astral.sh/uv/"
command -v node >/dev/null && command -v npm >/dev/null || die "install Node.js 22+ first"
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=12)||(a===20&&b>=19)?0:1)' \
  || die "Node $(node -v) is too old for Vite 8; install Node 22.12+ (or 20.19+)"
for port in 8000 5173; do
  if command -v lsof >/dev/null && lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    die "port $port is already in use (another dev.sh?). Stop it, e.g.: kill \$(lsof -tiTCP:$port -sTCP:LISTEN)"
  fi
done

(cd backend && uv sync --quiet)
# Reinstall when package-lock.json changed since the last install, not only when node_modules is missing.
if [ ! -f frontend/node_modules/.package-lock.json ] || [ frontend/package-lock.json -nt frontend/node_modules/.package-lock.json ]; then
  (cd frontend && npm ci --silent)
fi

cleanup() { trap - EXIT INT TERM; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM
(cd backend && uv run uvicorn planner.api:app --host 127.0.0.1 --port 8000 --reload) &
(cd frontend && npm run dev -- --port 5173 --strictPort) &
echo "Open http://localhost:5173  (API docs: http://localhost:8000/docs)"
wait
