#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "python or python3 is required for local smoke checks." >&2
    exit 1
  fi
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for local smoke checks." >&2
  exit 1
fi

echo "Running backend tests..."
"$PYTHON_BIN" -m pytest backend/tests -v

echo "Checking backend health endpoint..."
curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health"
echo

echo "Building frontend..."
npm --prefix frontend run build

echo "Checking frontend dev server root..."
curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null

echo "Lynjax local smoke checks passed."
