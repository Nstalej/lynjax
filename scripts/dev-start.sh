#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
PID_DIR="$ROOT/.dev-pids"
LOG_DIR="$ROOT/.dev-logs"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

mkdir -p "$PID_DIR" "$LOG_DIR"

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1
}

if is_running "$BACKEND_PID_FILE" || is_running "$FRONTEND_PID_FILE"; then
  echo "Lynjax dev environment appears to be running already."
  echo "Run: bash scripts/dev-stop.sh"
  exit 1
fi

if command -v netstat >/dev/null 2>&1; then
  if netstat -ano | grep -E "[.:]${BACKEND_PORT}[[:space:]]" | grep -q LISTENING; then
    echo "Backend port ${BACKEND_PORT} is already in use. Stop the existing process or set BACKEND_PORT=8010." >&2
    exit 1
  fi
  if netstat -ano | grep -E "[.:]${FRONTEND_PORT}[[:space:]]" | grep -q LISTENING; then
    echo "Frontend port ${FRONTEND_PORT} is already in use. Stop the existing process or set FRONTEND_PORT=5174." >&2
    exit 1
  fi
fi

if ! command -v python >/dev/null 2>&1; then
  echo "python is required to start the Lynjax backend." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to start the Lynjax frontend." >&2
  exit 1
fi

if [[ ! -d backend ]]; then
  echo "Missing backend/ directory." >&2
  exit 1
fi

if [[ ! -d frontend ]]; then
  echo "Missing frontend/ directory." >&2
  exit 1
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  npm --prefix frontend install
fi

echo "Starting Lynjax backend on http://127.0.0.1:${BACKEND_PORT}"
(
  cd backend
  python -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
) >"$LOG_DIR/backend.log" 2>&1 &
echo $! > "$BACKEND_PID_FILE"

echo "Starting Lynjax frontend on http://127.0.0.1:${FRONTEND_PORT}"
(
  cd frontend
  npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
) >"$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$FRONTEND_PID_FILE"

echo "Waiting for services..."
for i in $(seq 1 30); do
  backend_ok=0
  frontend_ok=0

  if command -v curl >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    backend_ok=1
  fi

  if command -v curl >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1; then
    frontend_ok=1
  fi

  if [[ "$backend_ok" -eq 1 && "$frontend_ok" -eq 1 ]]; then
    echo "Lynjax dev environment is ready."
    echo "Backend:  http://127.0.0.1:${BACKEND_PORT}/health"
    echo "API docs: http://127.0.0.1:${BACKEND_PORT}/docs"
    echo "Frontend: http://127.0.0.1:${FRONTEND_PORT}/"
    echo "Logs:     .dev-logs/backend.log and .dev-logs/frontend.log"
    echo "Stop:     bash scripts/dev-stop.sh"
    exit 0
  fi

  sleep 1
done

echo "Services did not become ready within 30 seconds." >&2
echo "Backend log:" >&2
tail -n 40 "$LOG_DIR/backend.log" >&2 || true
echo "Frontend log:" >&2
tail -n 40 "$LOG_DIR/frontend.log" >&2 || true
exit 1
