#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is required for the Lynjax lab smoke test." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for the Lynjax lab smoke test." >&2
  exit 1
fi

cleanup() {
  docker compose -f lab/docker/docker-compose.yml down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

bash scripts/lab_validate.sh

docker compose -f lab/docker/docker-compose.yml up -d

for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18080/ >/dev/null \
    && curl -fsS http://127.0.0.1:18081/metadata.json >/dev/null; then
    echo "Lynjax lab smoke test passed."
    exit 0
  fi
  echo "Waiting for lab targets... attempt $i/30"
  sleep 2
done

echo "Lynjax lab smoke test failed: targets did not become ready." >&2
docker compose -f lab/docker/docker-compose.yml ps >&2 || true
exit 1
