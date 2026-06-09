# Lynjax Local Test Environment

Guía para correr el ambiente local de pruebas de Lynjax beta 0.5 con backend FastAPI, frontend React/Vite y smoke checks básicos.

## Requisitos

- Windows con Git Bash, WSL o shell compatible con Bash.
- Python 3.11+.
- Node.js 20+ y npm.
- curl.
- Docker Compose opcional en WSL2/VM/CI si se quiere levantar el lab de targets locales en `lab/docker/`. Evitar instalar Docker directamente en Windows hasta aprobar el runtime/sandbox.

## Estructura relevante

```text
backend/   # FastAPI: health, info y endpoint demo de assessments simulados
frontend/  # React/Vite: dashboard visual Lynjax
scripts/   # dev-start, dev-stop, smoke-local y scripts del lab Docker
reports/   # plantillas y salidas de assessment
```

## 1. Instalar dependencias del backend

Desde la raíz del proyecto:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
python -m pip install -r backend/requirements.txt
```

O con venv aislado:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax/backend
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Instalar dependencias del frontend

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax/frontend
npm install
```

## 3. Levantar backend + frontend juntos

Desde la raíz:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/dev-start.sh
```

URLs esperadas:

- Backend health: `http://127.0.0.1:8000/health`
- Backend docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:5173/`

Logs:

```bash
tail -f .dev-logs/backend.log
tail -f .dev-logs/frontend.log
```

Detener servicios:

```bash
bash scripts/dev-stop.sh
```

## 4. Levantar servicios manualmente

Backend:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax/backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend en otra terminal:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## 5. Smoke checks básicos

Con backend y frontend ya levantados:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/smoke-local.sh
```

El script ejecuta:

```bash
python -m pytest backend/tests -v
curl -fsS http://127.0.0.1:8000/health
npm --prefix frontend run build
curl -fsS http://127.0.0.1:5173/ >/dev/null
```

Resultado esperado:

- `3 passed` en tests del backend.
- `/health` responde `{"status":"ok"}`.
- `npm run build` genera `frontend/dist/` sin errores.
- La raíz del frontend responde HTTP 200.

## 6. Lab Docker opcional

El lab Docker expone targets seguros/locales para demo de red sin tocar redes reales:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/lab_validate.sh
bash scripts/lab_up.sh
bash scripts/lab_smoke.sh
bash scripts/lab_down.sh
```

Targets esperados:

- `http://127.0.0.1:18080/`
- `http://127.0.0.1:18081/metadata.json`

## 7. Troubleshooting rápido

- Si `uvicorn` no existe: `python -m pip install -r backend/requirements.txt`.
- Si `vite` no existe: `npm --prefix frontend install`.
- Si un puerto está ocupado, usa variables:

```bash
BACKEND_PORT=8010 FRONTEND_PORT=5174 bash scripts/dev-start.sh
```

- Si `scripts/dev-start.sh` queda a medias:

```bash
bash scripts/dev-stop.sh
rm -rf .dev-pids
```
