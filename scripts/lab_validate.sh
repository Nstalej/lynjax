#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

required_files=(
  "lab/README.md"
  "lab/docker/docker-compose.yml"
  "lab/docker/target-web/index.html"
  "lab/docker/target-web/nginx.conf"
  "lab/docker/target-metadata/metadata.json"
  "lab/sample-data/assessment-scope.json"
  "lab/sample-data/targets.json"
  "lab/sample-data/expected-checks.json"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required lab file: $file" >&2
    exit 1
  fi
  echo "OK file: $file"
done

python - <<'PY'
from pathlib import Path
import json

for path in [
    Path("lab/sample-data/assessment-scope.json"),
    Path("lab/sample-data/targets.json"),
    Path("lab/sample-data/expected-checks.json"),
    Path("lab/docker/target-metadata/metadata.json"),
]:
    json.loads(path.read_text(encoding="utf-8"))
    print(f"JSON OK: {path.as_posix()}")
PY

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose -f lab/docker/docker-compose.yml config >/dev/null
  echo "Docker Compose config OK"
else
  echo "Docker Compose not available; skipped compose config validation."
fi

echo "Lynjax lab validation complete."
