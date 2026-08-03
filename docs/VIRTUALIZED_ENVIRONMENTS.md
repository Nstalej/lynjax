# Lynjax Beta 0.5 — Ambientes Virtualizados

## Objetivo

Definir una ruta segura para probar Lynjax sin contaminar Windows ni tocar redes reales. Windows queda como estación de control; el runtime del lab debe ejecutarse en una capa Linux aislada cuando sea posible.

## Principio operativo

Orden recomendado:

1. Validar en Git Bash/Windows con scripts locales.
2. Ejecutar Docker/Compose dentro de WSL2 Ubuntu/Debian o VM Ubuntu.
3. Usar una VM dedicada con snapshots si se requiere más aislamiento.
4. Preparar Containerlab como artefacto estático/visual después de estabilizar la beta local.
5. Ejecutar Containerlab solo dentro de WSL2 Ubuntu/Debian, VM Ubuntu o CI con Docker/Containerlab instalados de forma explícita.
6. Dejar GNS3/EVE-NG para una etapa posterior con recursos confirmados.

No se requiere instalar nada elevado desde estos scripts. Cualquier instalación de WSL2, Docker Desktop, VirtualBox, VMware, Hyper-V o cambios de BIOS requiere aprobación manual.

## Probe read-only del host

Antes de instalar o cambiar algo, ejecutar:

```bash
bash scripts/host-probe.sh
```

El script solo inspecciona disponibilidad de herramientas y estado básico. No habilita features, no instala paquetes y no modifica configuración.

## Ambiente A — Local directo para pruebas rápidas

Uso: validación de hoy sin contenedores.

```bash
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
bash scripts/dev-start.sh
bash scripts/smoke-local.sh
bash scripts/dev-stop.sh
```

Ventajas:

- Más rápido.
- Funciona en Git Bash.
- No requiere Docker para probar backend/frontend.

Límite:

- No levanta targets Docker del lab si Compose no está disponible.

## Ambiente B — WSL2 Ubuntu/Debian recomendado

Uso: ejecutar Compose dentro de Linux, con repo montado desde `/mnt/c/...` o clonado dentro de WSL.

Comandos esperados dentro de WSL:

```bash
cd /mnt/c/Users/nesal/Documents/001_Programas/lynjax
bash scripts/host-probe.sh
cd virtualization
bash run-beta-compose.sh up
```

URLs esperadas desde Windows:

- `http://127.0.0.1:5173/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:18080/`
- `http://127.0.0.1:18081/metadata.json`

Apagar:

```bash
cd virtualization
bash run-beta-compose.sh down
```

## Ambiente C — VM Ubuntu con snapshots

Uso: pruebas más aisladas o demos donde se quiere revertir estado.

Flujo:

1. Crear VM Ubuntu.
2. Crear snapshot limpio.
3. Instalar Git, Python, Node y Docker dentro de la VM.
4. Clonar repo.
5. Ejecutar checks locales y Compose beta.
6. Revertir snapshot si algo queda contaminado.

Comandos dentro de la VM:

```bash
git clone git@github.com:Nstalej/lynjax.git
cd lynjax
bash scripts/host-probe.sh
python -m pytest backend/tests -v
npm --prefix frontend install
npm --prefix frontend run build
cd virtualization
bash run-beta-compose.sh up
```

## Ambiente D — CI/GitHub Actions

Uso: validación reproducible sin depender del host local.

Workflows disponibles:

- `.github/workflows/backend-ci.yml`.
- `.github/workflows/frontend-ci.yml`.
- `.github/workflows/lab-ci.yml`.

El lab CI ejecuta Docker Compose en runner Ubuntu y valida los targets locales.

## Ambiente E — Containerlab preparado para inspección visual/Linux

Uso: revisar una topología demo sanitizada y dejar lista la ruta para pruebas base dentro de un runtime Linux.

Archivos:

- `docs/lab/CONTAINERLAB_PREP.md`.
- `virtualization/containerlab/README.md`.
- `virtualization/containerlab/lynjax-demo.clab.yml`.

Validación estática desde Git Bash/Windows o Linux:

```bash
bash scripts/lab_validate.sh
```

Inspección visual con VS Code:

```bash
code --list-extensions | grep -i '^srl-labs\.vscode-containerlab$'
code virtualization/containerlab/lynjax-demo.clab.yml
```

Comandos futuros solo dentro de WSL2 Ubuntu/Debian, VM Ubuntu o CI con Docker/Containerlab instalado:

```bash
containerlab inspect --topo virtualization/containerlab/lynjax-demo.clab.yml || true
sudo containerlab deploy --topo virtualization/containerlab/lynjax-demo.clab.yml
sudo containerlab inspect --topo virtualization/containerlab/lynjax-demo.clab.yml
sudo containerlab destroy --topo virtualization/containerlab/lynjax-demo.clab.yml --cleanup
```

Límites:

- No usar credenciales reales.
- No agregar IPs de clientes o públicas.
- No escanear redes externas.
- No desplegar desde Windows/Git Bash si Docker/Containerlab no existen dentro de una capa Linux aprobada.

## Compose beta

Archivo principal:

- `virtualization/docker-compose.beta.yml`

Wrapper:

- `virtualization/run-beta-compose.sh`

Servicios:

- `lynjax-backend`: FastAPI.
- `lynjax-frontend`: Vite dev server.
- `lynjax-target-web`: target nginx demo.
- `lynjax-target-metadata`: target metadata demo.

Comandos:

```bash
cd virtualization
bash run-beta-compose.sh config
bash run-beta-compose.sh up
bash run-beta-compose.sh ps
bash run-beta-compose.sh logs
bash run-beta-compose.sh down
```

## Criterios de aceptación

- Backend responde `GET /health`.
- Frontend responde en `5173`.
- Target web responde en `18080`.
- Target metadata responde en `18081/metadata.json`.
- `bash scripts/lab_validate.sh` pasa.
- `python -m pytest backend/tests -v` pasa.
- `npm --prefix frontend run build` pasa.

## Riesgos abiertos

- Docker/Compose puede no estar instalado en Windows/WSL/VM.
- El repo montado desde Windows a WSL puede ser más lento que clonarlo dentro de WSL.
- Vite en contenedor está pensado para demo/dev, no producción.
- El lab sigue siendo simulado; no debe venderse como scanner real.
