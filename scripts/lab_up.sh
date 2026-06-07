#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to start the Lynjax local lab." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is required to start the Lynjax local lab." >&2
  exit 1
fi

bash scripts/lab_validate.sh

docker compose -f lab/docker/docker-compose.yml up -d

echo "Lynjax local lab is starting."
echo "Target web:      http://localhost:18080/"
echo "Target metadata: http://localhost:18081/metadata.json"
docker compose -f lab/docker/docker-compose.yml ps
