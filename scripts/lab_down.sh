#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose not available; nothing to stop from this shell."
  exit 0
fi

docker compose -f lab/docker/docker-compose.yml down --remove-orphans

echo "Lynjax local lab stopped."
