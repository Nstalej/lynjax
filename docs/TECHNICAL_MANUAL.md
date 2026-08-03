# Lynjax v1.0-rc1 — Manual Técnico

## Arquitectura

Lynjax v1.0-rc1 está separado en capas simples y verificables:

- `backend/`: API FastAPI con contrato demo de assessment.
- `frontend/`: SPA React/Vite/TypeScript con shell de plataforma bilingüe.
- `lab/`: targets HTTP locales seguros.
- `virtualization/`: Compose beta para app + lab y topología Containerlab sanitizada.
- `scripts/`: automatización reproducible.
- `reports/`: plantilla y renderer Markdown.
- `docs/`: manuales, estado y release notes.

## Backend

Stack:

- Python 3.11+ / 3.12 en WSL.
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
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health` — contrato mínimo de vida.
- `GET /api/v1/info` — metadata del candidato.
- `POST /api/v1/assessments/connectivity-demo` — resultados demo estructurados y reporte Markdown.

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
- i18n ligero interno ES/EN.

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
- `scripts/lab_validate.sh`: valida fixtures, Containerlab estático y Compose si está disponible.
- `scripts/lab_up.sh`, `scripts/lab_smoke.sh`, `scripts/lab_down.sh`: lab Docker local legado.
- `scripts/host-probe.sh`: inspección read-only del host.
- `virtualization/run-beta-compose.sh`: wrapper de Docker Compose para stack v1.0-rc1.

Los scripts soportan `python` o `python3` vía `PYTHON_BIN`:

```bash
PYTHON_BIN=python3 bash scripts/smoke-local.sh
```

## Puertos

- Backend: `127.0.0.1:8000`.
- Frontend: `127.0.0.1:5173`.
- Lab target web: `127.0.0.1:18080`.
- Lab target metadata: `127.0.0.1:18081`.

Variables soportadas:

```bash
BACKEND_PORT=8010 FRONTEND_PORT=5174 bash scripts/dev-start.sh
```

## Validación completa local

```bash
python -m pytest backend/tests -v
npm --prefix frontend install
npm --prefix frontend run build
bash -n scripts/*.sh virtualization/run-beta-compose.sh
bash scripts/lab_validate.sh
bash scripts/dev-start.sh
bash scripts/smoke-local.sh
bash scripts/dev-stop.sh
```

## WSL2/Ubuntu + Docker Compose

Validado en WSL2 Ubuntu con Docker/Compose disponibles:

```bash
cd /mnt/c/Users/nesal/Documents/001_Programas/lynjax
. /home/nstalej/.nvm/nvm.sh
nvm use 24
backend/.venv-wsl/bin/python -m pytest backend/tests -v
npm --prefix frontend install
npm --prefix frontend run build
bash scripts/lab_validate.sh
cd virtualization
bash run-beta-compose.sh config
bash run-beta-compose.sh up-detached
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:5173/ >/dev/null
curl -fsS http://127.0.0.1:18080/ >/dev/null
curl -fsS http://127.0.0.1:18081/metadata.json >/dev/null
bash run-beta-compose.sh down -v
```

## Containerlab

Artefacto preparado:

- `virtualization/containerlab/lynjax-demo.clab.yml`

Validación actual:

- Static sanity: PASS.
- Runtime `containerlab`: SKIP porque no está instalado en WSL2.

Comandos futuros dentro de Linux runtime aprobado:

```bash
containerlab inspect --topo virtualization/containerlab/lynjax-demo.clab.yml || true
sudo containerlab deploy --topo virtualization/containerlab/lynjax-demo.clab.yml
sudo containerlab destroy --topo virtualization/containerlab/lynjax-demo.clab.yml --cleanup
```

## CI esperado

- Backend CI: compile/test API.
- Frontend CI: install/build.
- Lab CI: static lab validation y Compose config/checks cuando Docker exista.

## Dependency audit

`npm audit --audit-level=high` reporta 2 vulnerabilidades high por `esbuild` vía Vite. No se aplicó `npm audit fix --force` porque propone Vite 8, upgrade mayor/breaking. Recomendación: crear rama separada para evaluar Vite 8, ajustar Node/CI y volver a correr smoke completo.

## Troubleshooting

- `uvicorn: command not found`: instalar `backend/requirements.txt` en el Python activo.
- `vite: command not found`: ejecutar `npm --prefix frontend install`.
- Rollup optional dependency missing: ejecutar `npm --prefix frontend install` en el mismo OS donde se hará el build.
- Puerto ocupado: usar `BACKEND_PORT` / `FRONTEND_PORT` o `bash scripts/dev-stop.sh`.
- Docker no disponible en Git Bash: usar WSL2/Ubuntu/VM/CI.
- `containerlab: command not found`: instalar solo dentro del runtime Linux aprobado.
- Errores CRLF en WSL: `.gitattributes` normaliza LF; hacer checkout limpio o re-clonar si queda un working tree antiguo.
