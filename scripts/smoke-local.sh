#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for local smoke checks." >&2
  exit 1
fi

echo "Running backend tests..."
python -m pytest backend/tests -v

echo "Checking backend health endpoint..."
curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health"
echo

echo "Building frontend..."
npm --prefix frontend run build

echo "Checking frontend dev server root..."
curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null

echo "Lynjax local smoke checks passed."
