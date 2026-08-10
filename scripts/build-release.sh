#!/usr/bin/env bash
# Build the distributable artifacts.
#
# The frontend must be compiled and copied into the package *before* the wheel
# is built, or the wheel ships an API with no interface. That step is easy to
# forget by hand, which is why this script exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Building the frontend"
(cd frontend && npm ci --silent && npm run build)

echo "==> Bundling the frontend into the package"
rm -rf backend/lynjax/web
cp -r frontend/dist backend/lynjax/web

echo "==> Building the wheel and sdist"
cd backend
rm -rf dist build
"${PYTHON:-python}" -m build

echo
echo "==> Artifacts"
ls -lh dist/

echo
echo "Verify the interface really shipped:"
"${PYTHON:-python}" - <<'PY'
import glob, zipfile
wheel = glob.glob("dist/*.whl")[0]
names = zipfile.ZipFile(wheel).namelist()
web = [n for n in names if "/web/" in n]
print(f"  {wheel}: {len(web)} interface file(s)")
raise SystemExit(0 if web else "The wheel has no interface. The bundling step did not run.")
PY
