# Lynjax

**Lynjax — Intelligent Network Visibility** es la beta limpia derivada del rebrand de NetVault: una base para auditoría, assessment y trazabilidad de infraestructura de red real, empezando por un flujo seguro, local y verificable.

> Estado actual: **beta 0.5 lista para pruebas locales** con backend FastAPI, frontend React/Vite, lab Docker Compose local, scripts de arranque/parada, smoke checks y manuales operativos.

## Qué incluye esta beta

- **Backend (`backend/`)**: API FastAPI con health check, metadata de beta y endpoint demo de assessment simulado.
- **Frontend (`frontend/`)**: dashboard React/Vite con identidad visual Lynjax.
- **Lab (`lab/`)**: targets HTTP locales/sanitizados para pruebas repetibles sin tocar redes reales.
- **Virtualización (`virtualization/`)**: Compose beta para levantar backend + frontend + lab desde un runtime Linux/Docker aislado.
- **Documentación (`docs/`)**: manual de usuario, manual técnico, guía de pruebas locales y guía de ambientes virtualizados.
- **Reportes (`reports/`)**: plantilla markdown inicial para reportes técnicos de assessment.
- **Scripts (`scripts/`)**: arranque, parada, smoke checks, validación del lab y probe read-only del host.
- **CI (`.github/workflows/`)**: checks de backend, frontend y lab.

## Límites de seguridad

Esta versión es una **beta técnica de laboratorio**:

- No escanea redes externas.
- No usa credenciales reales.
- No debe ejecutarse contra clientes sin autorización escrita.
- El endpoint de assessment es simulado y devuelve evidencia demo.
- Los targets del lab se publican solo en `127.0.0.1`.

## Inicio rápido para pruebas de hoy

Desde Git Bash/WSL en Windows:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax

# Backend dependencies
python -m pip install -r backend/requirements.txt

# Frontend dependencies
npm --prefix frontend install

# Levantar backend + frontend
bash scripts/dev-start.sh
```

Abrir:

- Frontend: `http://127.0.0.1:5173/`
- Backend health: `http://127.0.0.1:8000/health`
- Backend docs/OpenAPI: `http://127.0.0.1:8000/docs`

Verificar:

```bash
bash scripts/smoke-local.sh
```

Detener:

```bash
bash scripts/dev-stop.sh
```

## Ejecutar backend manualmente

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Git Bash en Windows
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`
- `GET /api/v1/info`
- `POST /api/v1/assessments/connectivity-demo`

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessments/connectivity-demo \
  -H 'Content-Type: application/json' \
  -d '{"hosts":["target-web","target-metadata"],"checks":["http","dns"]}'
```

## Ejecutar frontend manualmente

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Build de producción:

```bash
npm --prefix frontend run build
```

## Lab local

```bash
bash scripts/lab_validate.sh
bash scripts/lab_up.sh
bash scripts/lab_smoke.sh
bash scripts/lab_down.sh
```

Targets esperados:

- `http://127.0.0.1:18080/`
- `http://127.0.0.1:18081/metadata.json`

## Ambiente virtualizado beta

Para levantar app + lab desde Docker/Compose dentro de WSL2 o una VM Ubuntu:

```bash
bash scripts/host-probe.sh
cd virtualization
bash run-beta-compose.sh up
```

Ver detalles en `docs/VIRTUALIZED_ENVIRONMENTS.md`.

## Tests y validación

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
bash scripts/lab_validate.sh
```

Smoke completo con servicios locales ya levantados:

```bash
bash scripts/smoke-local.sh
```

## Manuales

- Usuario/demo: `docs/USER_MANUAL.md`
- Técnico/operación: `docs/TECHNICAL_MANUAL.md`
- Ambiente local: `docs/LOCAL_TEST_ENVIRONMENT.md`
- Virtualización: `docs/VIRTUALIZED_ENVIRONMENTS.md`
- Estado beta: `docs/BETA_0_5_STATUS.md`
- LaTeX/PDF con capturas virtuales: `docs/manual/latex/lynjax-beta-0.5-manual.tex` y `docs/manual/lynjax-beta-0.5-manual.pdf`

## Roadmap inmediato

1. Conectar frontend al endpoint real `/api/v1/assessments/connectivity-demo`.
2. Generar reporte markdown desde datos devueltos por la API.
3. Añadir persistencia local mínima para ejecuciones/evidencias.
4. Crear checklist de autorización/scope para beta de campo controlada.
5. Agregar checks TCP/SSH seguros antes de SNMP o integraciones más invasivas.
