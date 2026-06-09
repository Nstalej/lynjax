#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/virtualization/docker-compose.beta.yml"
ACTION="${1:-up}"
shift || true

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Run scripts/host-probe.sh first and use WSL2/Ubuntu VM/CI when possible." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required." >&2
  exit 1
fi

case "$ACTION" in
  up)
    docker compose -f "$COMPOSE_FILE" up --build "$@"
    ;;
  up-detached|upd)
    docker compose -f "$COMPOSE_FILE" up --build -d "$@"
    ;;
  down)
    docker compose -f "$COMPOSE_FILE" down --remove-orphans "$@"
    ;;
  restart)
    docker compose -f "$COMPOSE_FILE" down --remove-orphans
    docker compose -f "$COMPOSE_FILE" up --build "$@"
    ;;
  logs)
    docker compose -f "$COMPOSE_FILE" logs -f "$@"
    ;;
  ps)
    docker compose -f "$COMPOSE_FILE" ps "$@"
    ;;
  config)
    docker compose -f "$COMPOSE_FILE" config "$@"
    ;;
  *)
    echo "Usage: bash virtualization/run-beta-compose.sh [up|up-detached|upd|down|restart|logs|ps|config]" >&2
    exit 2
    ;;
esac
