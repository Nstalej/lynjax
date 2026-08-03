# Lynjax v1.0-rc1 Status

Fecha de corte: 2026-06-15

## Resumen

Lynjax queda preparado como **v1.0-rc1**, no como v1.0 final. El candidato puede ejecutarse localmente en Windows/Git Bash para pruebas base de frontend/backend y también fue validado en WSL2 Ubuntu con Docker Compose para el stack app + lab. No se ejecutaron escaneos externos, no se usaron credenciales reales y no se instalaron componentes de host.

## Alcance incluido

- Shell visual React/Vite bilingüe ES/EN con sidebar, topbar y módulos reservados.
- Módulos visibles: Resumen, Activos, Conectividad, Assessments, Evidencia, Reportes, Topología, Directorio/AD, Inteligencia/LLM y Configuración.
- Backend FastAPI con health, metadata y endpoint seguro `POST /api/v1/assessments/connectivity-demo`.
- Reporte Markdown generado desde la respuesta estructurada del assessment demo.
- Scripts de arranque/parada/smoke local.
- Artefactos Docker Compose y Containerlab sanitizados para lab virtual/container.
- Manuales Markdown, notas de release y manual LaTeX/PDF si el toolchain local lo permite.

## Matriz de validación ejecutada

| Validación | Entorno | Resultado | Notas |
|---|---:|---:|---|
| `git pull --ff-only` | Git Bash/Windows | PASS | `main` ya estaba actualizado antes de cambios Day 5. |
| `python -m pytest backend/tests -v` | Git Bash/Windows | PASS | 5 tests pasaron. |
| `npm --prefix frontend run build` | Git Bash/Windows | PASS | Vite build OK. Se requirió `npm --prefix frontend install` para rehidratar dependencia opcional de Rollup. |
| `bash -n scripts/*.sh virtualization/run-beta-compose.sh` | Git Bash/Windows | PASS | Sintaxis shell OK. |
| `bash scripts/lab_validate.sh` | Git Bash/Windows | PASS | Validación estática OK; Docker Compose omitido porque `docker` no existe en PATH Windows/Git Bash. |
| `bash scripts/dev-start.sh && bash scripts/smoke-local.sh && bash scripts/dev-stop.sh` | Git Bash/Windows | PASS | Backend, frontend y smoke local OK. |
| `backend/.venv-wsl/bin/python -m pytest backend/tests -v` | WSL2 Ubuntu | PASS | 5 tests pasaron; warning deprecación Starlette/httpx. |
| `npm --prefix frontend run build` | WSL2 Ubuntu con nvm Node 24 | PASS | Build OK tras `npm install`. |
| `bash scripts/lab_validate.sh` | WSL2 Ubuntu | PASS | Incluyó `Docker Compose config OK`. |
| `bash virtualization/run-beta-compose.sh config` | WSL2 Ubuntu + Docker | PASS | Compose config renderizó correctamente. |
| `bash virtualization/run-beta-compose.sh up-detached` + HTTP smoke | WSL2 Ubuntu + Docker | PASS | Health backend, frontend, target web y metadata respondieron en localhost. |
| `containerlab version` | WSL2 Ubuntu | SKIP | `containerlab` no está instalado; solo se validó la topología de forma estática. |
| `npm audit --audit-level=high` | Windows/WSL | WARN | 2 hallazgos high por `esbuild` vía Vite; `npm audit fix --force` propone Vite 8 (breaking), no aplicado automáticamente. |

## Comandos reproducibles

### Validación local Windows/Git Bash

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
python -m pytest backend/tests -v
npm --prefix frontend install
npm --prefix frontend run build
bash -n scripts/*.sh virtualization/run-beta-compose.sh
bash scripts/lab_validate.sh
bash scripts/dev-start.sh
bash scripts/smoke-local.sh
bash scripts/dev-stop.sh
```

### Validación WSL2 Ubuntu con Docker

```bash
cd /mnt/c/Users/nesal/Documents/001_Programas/lynjax
. /home/nstalej/.nvm/nvm.sh
nvm use 24
backend/.venv-wsl/bin/python -m pytest backend/tests -v
npm --prefix frontend install
npm --prefix frontend run build
bash -n scripts/*.sh virtualization/run-beta-compose.sh
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

## Readiness virtual/container lab

- WSL2 Ubuntu está disponible y Docker/Compose funcionan en WSL.
- Containerlab no está instalado; el archivo `virtualization/containerlab/lynjax-demo.clab.yml` queda como artefacto sanitizado y validado estáticamente.
- La ejecución real de Containerlab debe hacerse solo después de instalarlo explícitamente dentro de WSL2/Ubuntu/VM, no en Windows host.
- Los puertos publicados son localhost: `8000`, `5173`, `18080`, `18081`.

## Riesgos abiertos

1. **Release candidate, no final:** publicar `v1.0` final requiere aprobación explícita de Alejandro después de pruebas manuales.
2. **NPM audit:** quedan 2 vulnerabilidades high reportadas por `npm audit` en la cadena Vite/esbuild. No se aplicó `npm audit fix --force` porque propone upgrade mayor/breaking.
3. **Containerlab runtime:** falta instalar/probar `containerlab` en WSL2/Ubuntu o VM.
4. **Backend version boundary:** la API fue actualizada a `1.0.0-rc1`; revisar todo copy externo si aún menciona beta 0.5.
5. **Line endings:** se agregó `.gitattributes` y se normalizaron archivos de texto a LF para que WSL/Linux pueda ejecutar scripts sin errores CRLF.

## Próximos pasos manuales para Alejandro

1. Abrir `http://127.0.0.1:5173/` y validar navegación/sidebar, responsive y selector ES/EN.
2. Ejecutar el CTA de demo segura y confirmar que renderiza datos reales del backend.
3. Abrir `http://127.0.0.1:8000/docs` y probar `POST /api/v1/assessments/connectivity-demo`.
4. En WSL2, ejecutar el bloque Compose anterior y verificar los cuatro endpoints localhost.
5. Decidir si se acepta el riesgo temporal de Vite/esbuild para rc1 o si se agenda una rama separada para evaluar Vite 8/upgrade seguro antes del final.
6. Si se quiere Containerlab real, aprobar instalación dentro de WSL2/Ubuntu o usar una VM desechable.
