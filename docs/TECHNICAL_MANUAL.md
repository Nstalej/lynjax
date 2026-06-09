# Lynjax Beta 0.5 — Manual Técnico

## Arquitectura actual

Lynjax beta 0.5 está separada en capas simples:

- `backend/`: API FastAPI.
- `frontend/`: SPA React/Vite.
- `lab/`: targets locales seguros para pruebas.
- `virtualization/`: Compose beta para app + lab en runtime Linux/Docker.
- `scripts/`: automatización reproducible.
- `reports/`: plantillas de salida.

## Backend

Stack:

- Python 3.11+ compatible.
- FastAPI.
- Uvicorn.
- Pydantic.
- Pytest + HTTPX para tests.

Instalación:

```bash
python -m pip install -r backend/requirements.txt
```

Ejecución:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`: contrato mínimo de vida.
- `GET /api/v1/info`: metadata de beta.
- `POST /api/v1/assessments/connectivity-demo`: resultados simulados.

Tests:

```bash
python -m pytest backend/tests -v
```

## Frontend

Stack:

- React.
- TypeScript.
- Vite.
- CSS propio con tokens Lynjax.

Instalación:

```bash
npm --prefix frontend install
```

Desarrollo:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Build:

```bash
npm --prefix frontend run build
```

## Scripts operativos

- `scripts/dev-start.sh`: arranca backend y frontend, guarda PID/logs.
- `scripts/dev-stop.sh`: detiene servicios locales.
- `scripts/smoke-local.sh`: valida backend, health, build frontend y HTTP frontend.
- `scripts/lab_validate.sh`: valida fixtures y Compose si está disponible.
- `scripts/lab_up.sh`: levanta targets demo.
- `scripts/lab_smoke.sh`: levanta, prueba y destruye lab.
- `scripts/lab_down.sh`: baja targets demo.
- `scripts/host-probe.sh`: inspección read-only del host para virtualización.

## Puertos

- Backend: `127.0.0.1:8000`.
- Frontend: `127.0.0.1:5173`.
- Lab target web: `127.0.0.1:18080`.
- Lab target metadata: `127.0.0.1:18081`.

Variables soportadas por scripts dev:

```bash
BACKEND_PORT=8010 FRONTEND_PORT=5174 bash scripts/dev-start.sh
```

## Lab local

El lab define dos servicios HTTP locales:

- `target-web`: nginx con landing demo.
- `target-metadata`: Python HTTP server con `metadata.json`.

Validación:

```bash
bash scripts/lab_validate.sh
```

Smoke:

```bash
bash scripts/lab_smoke.sh
```

## Ambiente virtualizado app + lab

Desde una capa Linux con Docker Compose:

```bash
cd virtualization
bash run-beta-compose.sh up
```

Esto levanta:

- `lynjax-backend` en `127.0.0.1:8000`.
- `lynjax-frontend` en `127.0.0.1:5173`.
- Targets demo en `127.0.0.1:18080` y `127.0.0.1:18081`.

Apagar:

```bash
cd virtualization
bash run-beta-compose.sh down
```

## CI esperado

- Backend CI: instala dependencias, ejecuta Ruff si hay Python, compileall y pytest.
- Frontend CI: npm install/ci, lint/test si existen, build.
- Lab CI: valida fixtures, levanta Compose, prueba targets y destruye containers.

## Checklist antes de probar

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
bash scripts/lab_validate.sh
```

Si backend + frontend están levantados:

```bash
bash scripts/smoke-local.sh
```

## Troubleshooting

- `uvicorn: command not found`: instalar `backend/requirements.txt`.
- `vite: command not found`: ejecutar `npm --prefix frontend install`.
- Puerto ocupado: usar `BACKEND_PORT` / `FRONTEND_PORT` o `bash scripts/dev-stop.sh`.
- Docker no disponible: usar solo `dev-start` + `smoke-local`; el lab Compose queda pendiente hasta WSL2/VM/CI.
- En Git Bash Windows, preferir rutas `/c/Users/...` para comandos bash.

## Criterio de listo para pruebas del día

La beta se considera lista cuando pasan:

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
bash scripts/lab_validate.sh
```

Y, con servicios levantados:

```bash
bash scripts/smoke-local.sh
```
