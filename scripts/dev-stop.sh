#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT/.dev-pids"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

stop_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name: no pid file."
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Stopping $name shell process (pid $pid)..."
    kill "$pid" >/dev/null 2>&1 || true
  else
    echo "$name: pid $pid is not running."
  fi

  rm -f "$pid_file"
}

stop_windows_pid_on_port() {
  local name="$1"
  local port="$2"

  if ! command -v netstat >/dev/null 2>&1; then
    return 0
  fi

  local listeners
  listeners="$(netstat -ano | grep -E "[.:]${port}[[:space:]]" | grep LISTENING || true)"
  if [[ -z "$listeners" ]]; then
    return 0
  fi

  while read -r proto local_addr foreign_addr state pid; do
    if [[ -n "${pid:-}" && "$pid" != "0" ]]; then
      echo "Stopping $name listener on port $port (pid $pid)..."
      if command -v taskkill.exe >/dev/null 2>&1; then
        taskkill.exe //PID "$pid" //F >/dev/null 2>&1 || true
      else
        kill "$pid" >/dev/null 2>&1 || true
      fi
    fi
  done <<< "$listeners"
}

stop_pid_file "frontend" "$PID_DIR/frontend.pid"
stop_pid_file "backend" "$PID_DIR/backend.pid"
stop_windows_pid_on_port "frontend" "$FRONTEND_PORT"
stop_windows_pid_on_port "backend" "$BACKEND_PORT"

rmdir "$PID_DIR" >/dev/null 2>&1 || true

echo "Lynjax dev environment stopped."
