# Lynjax

**Lynjax — Intelligent Network Visibility** es la base limpia del rebrand de NetVault: una plataforma local/sandbox-first para convertir assessments de red en evidencia, reportes y una ruta de laboratorio virtual/container.

> Repositorio/carpeta canónica: `C:/Users/nesal/Documents/001_Programas/lynjax` (`git@github.com:Nstalej/lynjax.git`).
> Workspaces anteriores, todos retirados y no utilizables para desarrollo:
> - `001_Programas/netvault-rebrand-lab/lynjax` — envoltorio previo, retirado el 2026-07-31.
> - `001_Programas/lynjax` (versión de julio) — archivada en `_archived_workspaces/lynjax-external-migrated-20260706`.
> - `001_Programas/netvault` — línea original, respaldada en `_archived_workspaces/netvault-final-20260731`; su repo quedó archivado en GitHub.

> Estado actual: **cáscara de plataforma con checks simulados.** El backend ejecuta FastAPI con un
> endpoint demo seguro, el frontend React/Vite renderiza el flujo assessment→evidencia→reporte, y
> existen smoke checks y stack Docker Compose. Los checks devuelven `simulated-pass`: **todavía no
> hay conectividad real de red.** El motor validado (SNMP, SSH, REST, vault de credenciales, MCP,
> agente de Windows AD) se migra desde NetVault según `docs/plans/`.

## Qué incluye v1.0-rc1

- **Backend (`backend/`)**: API FastAPI con health, metadata y endpoint demo seguro `POST /api/v1/assessments/connectivity-demo`.
- **Frontend (`frontend/`)**: shell React/Vite bilingüe ES/EN con sidebar, topbar y módulos Lynjax.
- **Flujo demo**: el frontend puede llamar al backend y renderizar datos estructurados + reporte Markdown.
- **Lab (`lab/`)**: targets HTTP locales/sanitizados para pruebas repetibles.
- **Virtualización (`virtualization/`)**: Docker Compose beta para WSL2/Ubuntu/VM/CI y topología Containerlab sanitizada.
- **Documentación (`docs/`)**: manuales, estado v1.0-rc1, preparación de Containerlab y notas de release.
- **Scripts (`scripts/`)**: arranque/parada, smoke checks, validación de lab y probe read-only del host.
- **CI (`.github/workflows/`)**: checks de backend/frontend/lab.

## Límites de seguridad

Esta versión es una **release candidate técnica de laboratorio**:

- No escanea redes externas.
- No usa credenciales reales.
- No instala Docker/WSL/Containerlab/Windows features.
- No debe ejecutarse contra clientes sin autorización escrita.
- AD/LLM aparecen como módulos planificados/read-only, no como integraciones activas.
- Los targets del lab se publican solo en localhost.

## Inicio rápido local — Windows/Git Bash

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
bash scripts/dev-start.sh
```

Abrir:

- Frontend: `http://127.0.0.1:5173/`
- Backend health: `http://127.0.0.1:8000/health`
- Backend docs/OpenAPI: `http://127.0.0.1:8000/docs`

Verificar y detener:

```bash
bash scripts/smoke-local.sh
bash scripts/dev-stop.sh
```

## Tests y validación base

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
bash -n scripts/*.sh virtualization/run-beta-compose.sh
bash scripts/lab_validate.sh
```

## WSL2/Ubuntu + Docker Compose

Usar cuando Docker esté disponible dentro de WSL2/Ubuntu/VM/CI:

```bash
cd /mnt/c/Users/nesal/Documents/001_Programas/lynjax
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

## Endpoint demo

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessments/connectivity-demo \
  -H 'Content-Type: application/json' \
  -d '{"hosts":["target-web","target-metadata"],"checks":["http","dns"]}'
```

## Manuales y release candidate

- Estado v1.0-rc1: `docs/V1_0_STATUS.md`
- Notas de release: `docs/releases/v1.0-rc1-release-notes.md`
- Usuario/demo: `docs/USER_MANUAL.md`
- Técnico/operación: `docs/TECHNICAL_MANUAL.md`
- Preparación Containerlab: `docs/lab/CONTAINERLAB_PREP.md`
- Manual LaTeX/PDF: `docs/manual/latex/lynjax-v1.0-manual.tex` y `docs/manual/lynjax-v1.0-manual.pdf`

## Riesgos abiertos

- `npm audit --audit-level=high` reporta 2 hallazgos high por `esbuild` vía Vite; no se aplicó upgrade forzado porque propone Vite 8/breaking.
- Containerlab no está instalado en el WSL actual; la topología está validada estáticamente.
- Publicar `v1.0` final requiere aprobación explícita de Alejandro.
