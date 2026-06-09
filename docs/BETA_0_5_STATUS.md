# Lynjax Beta 0.5 Status

Fecha de actualización: 2026-06-09

## Estado ejecutivo

Lynjax beta 0.5 queda con un ambiente local ejecutable para demo técnica: backend FastAPI, frontend React/Vite, scripts de arranque/parada, smoke checks básicos y plantilla inicial de reporte de assessment.

## Componentes disponibles

### Backend — `backend/`

- FastAPI inicial en `backend/app/main.py`.
- Health check: `GET /health`.
- Metadata beta: `GET /api/v1/info`.
- Endpoint demo seguro/simulado: `POST /api/v1/assessments/connectivity-demo`.
- Tests de contrato en `backend/tests/test_api_baseline.py`.

### Frontend — `frontend/`

- React/Vite con dashboard visual Lynjax.
- Build TypeScript/Vite funcional.
- Datos mock de assessment en `frontend/src/lib/brand.ts` y vista en `frontend/src/pages/LynjaxDashboard.tsx`.

### Ambiente local — `scripts/`

- `scripts/dev-start.sh`: levanta backend + frontend en puertos locales.
- `scripts/dev-stop.sh`: detiene servicios y limpia listeners de los puertos configurados.
- `scripts/smoke-local.sh`: ejecuta tests backend, `/health`, build frontend y check HTTP del frontend.

### Reporte técnico — `reports/templates/`

- `reports/templates/assessment-report.md`: plantilla técnica base Lynjax para reportes beta.

### Documentación — `docs/`

- `docs/USER_MANUAL.md`: flujo de demo y prueba para usuarios/revisores.
- `docs/TECHNICAL_MANUAL.md`: operación técnica de backend, frontend, lab, CI y troubleshooting.
- `docs/LOCAL_TEST_ENVIRONMENT.md`: pasos exactos para instalar, arrancar, verificar y apagar el ambiente local.
- `docs/VIRTUALIZED_ENVIRONMENTS.md`: ruta WSL2/VM/CI y Compose beta para app + lab.
- `docs/manual/latex/lynjax-beta-0.5-manual.tex`: manual LaTeX con capturas virtuales.
- `docs/manual/lynjax-beta-0.5-manual.pdf`: versión PDF generada desde LaTeX.
- `docs/manual/assets/screenshots/`: capturas virtuales de frontend y backend.

### Virtualización — `virtualization/`

- `virtualization/docker-compose.beta.yml`: stack beta con backend, frontend y targets demo.
- `virtualization/run-beta-compose.sh`: wrapper para `config`, `up`, `down`, `logs` y `ps`.
- `scripts/host-probe.sh`: probe read-only del host antes de instalar o modificar virtualización.

## Current Baseline

Comandos ejecutados durante Día 5 / preparación final de pruebas:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/host-probe.sh
```

Resultado: probe read-only ejecutado; Python, Node, npm, curl, git, `wsl.exe` y `winget.exe` disponibles; Docker/VBox/Vagrant/Multipass/QEMU/GNS3 no disponibles desde Git Bash; virtualización firmware reportada como `False`; usuario no administrador.

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash -n scripts/host-probe.sh virtualization/run-beta-compose.sh
```

Resultado: scripts shell válidos.

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
python -m pytest backend/tests -v
```

Resultado: `3 passed`.

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax/frontend
npm run build
```

Resultado: build correcto con Vite; salida generada en `frontend/dist/`.

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/health
```

Resultado: `/health` respondió `{"status":"ok"}`.

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/dev-start.sh
bash scripts/smoke-local.sh
bash scripts/dev-stop.sh
```

Resultado: ambiente backend + frontend arrancó, smoke local pasó y los listeners en `8000`/`5173` fueron detenidos.

## Comandos recomendados para Alejandro

Arrancar todo:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/dev-start.sh
```

Abrir:

- Frontend: `http://127.0.0.1:5173/`
- Backend health: `http://127.0.0.1:8000/health`
- Backend docs: `http://127.0.0.1:8000/docs`

Verificar:

```bash
bash scripts/smoke-local.sh
```

Detener:

```bash
bash scripts/dev-stop.sh
```

## Pendientes

1. Conectar frontend a endpoints reales del backend en vez de usar únicamente mocks.
2. Generar un reporte real desde datos del endpoint demo usando `reports/templates/assessment-report.md`.
3. Definir modelo persistente mínimo para assessments/evidencias: JSON local o SQLite.
4. Añadir CORS/configuración de API URL cuando el frontend consuma backend desde navegador.
5. Validar `virtualization/docker-compose.beta.yml` en WSL2/VM/CI con Docker Compose disponible.
6. Decidir si `frontend/dist/` se conserva como artefacto local o se ignora con `.gitignore`.

## Open Risks

- Hay cambios sin commit en backend, frontend y documentación; revisar antes de publicar o crear release.
- `scripts/dev-stop.sh` incluye lógica específica para Windows/Git Bash usando `taskkill.exe` cuando hay listeners nativos; validar en WSL/Linux si se migra el flujo.
- La beta aún usa checks simulados; no debe presentarse como scanner de producción.
- El reporte es plantilla base; todavía no hay pipeline automático de generación desde datos reales.
- No hay autenticación ni manejo de credenciales; no usar con datos sensibles de clientes todavía.

## Próximos hitos sugeridos

### Hito 0.6 — Flujo end-to-end mínimo

- Crear assessment desde frontend.
- Enviar payload al endpoint demo.
- Mostrar resultados devueltos por API.
- Exportar markdown de reporte con datos simulados.

### Hito 0.7 — Evidencia y persistencia local

- Guardar ejecuciones en SQLite o JSON local.
- Vincular hallazgos con evidencia/timestamp.
- Añadir purga local de evidencia.

### Hito 0.8 — Beta de campo controlada

- Checklist de autorización.
- Scope explícito por assessment.
- Checks seguros contra targets autorizados.
- Reporte técnico sanitizado listo para entrega.
