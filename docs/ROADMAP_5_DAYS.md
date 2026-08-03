# Lynjax Roadmap 5 Días

> Plan de rescate/rebrand para convertir la idea NetVault en una base limpia de producto Lynjax beta 0.5.

## Current Baseline

- Ruta de trabajo inspeccionada: `C:\Users\nesal\Documents\001_Programasynjax`.
- Contenido existente antes de Lynjax: documentos de branding y `brand-kit-minimum/`.
- Repositorio Git: `lynjax/` ya está inicializado y conectado a `Nstalej/lynjax` en GitHub público.
- CI base: backend, frontend y lab tienen workflows separados.
- Decisión: tratar NetVault/brand-kit existente como referencia histórica, no como migración automática.

## Día 1 — Base limpia de producto y marca

**Objetivo:** Crear la estructura inicial de Lynjax sin arrastrar deuda de NetVault.

- Crear carpetas base: `backend/`, `frontend/`, `docs/`, `brand/`, `reports/`, `lab/`, `scripts/`, `.github/workflows/`.
- Crear README principal con visión, módulos y comandos previstos.
- Documentar arquitectura beta 0.5.
- Documentar este roadmap de 5 días.
- Crear READMEs mínimos para backend y frontend.
- Crear `.gitignore` adecuado para Python, Node, entornos locales, reportes generados y artefactos.

**Resultado esperado:** Estructura navegable y lista para empezar desarrollo TDD.

## Día 2 — Backend FastAPI mínimo

**Objetivo:** Levantar una API mínima verificable.

- Crear proyecto FastAPI dentro de `backend/`.
- Añadir endpoint `GET /health`.
- Añadir modelos iniciales para `Assessment`, `Target`, `CheckRun` y `Evidence` solo si son necesarios para el flujo beta.
- Añadir tests con `pytest` y `httpx`/`TestClient`.
- Añadir script `scripts/smoke_backend.sh`.
- Preparar workflow CI de backend.

**Resultado esperado:** `pytest` pasa y `GET /health` responde localmente.

## Día 3 — Frontend React/Vite mínimo

**Objetivo:** Crear una UI funcional para demostrar la narrativa del producto.

- Crear app React/Vite dentro de `frontend/`.
- Crear pantalla de inicio con propuesta de valor Lynjax.
- Crear dashboard básico con estados de assessment mockeados.
- Conectar health check del backend si está disponible.
- Añadir lint/test básico.
- Preparar workflow CI de frontend.

**Resultado esperado:** `npm run dev` muestra una demo limpia y entendible.

## Día 4 — Flujo de assessment y reportes beta

**Objetivo:** Definir el flujo de campo/lab y generar evidencia trazable.

- Documentar flujo: autorización, alcance, credenciales, checks, evidencia, reporte y purga.
- Crear plantilla de reporte en `reports/templates/`.
- Añadir endpoint o script inicial para producir un reporte markdown/JSON desde datos mock o fixtures.
- Añadir fixtures de lab en `lab/`.
- Añadir smoke script end-to-end mínimo.

**Resultado esperado:** Una demo puede producir un reporte de assessment sanitizado.

**Preparación adelantada:** El lab local Docker ya cuenta con targets HTTP seguros, fixtures de scope/targets/checks y scripts `lab_validate`, `lab_up`, `lab_smoke` y `lab_down` para que Día 4 pueda enfocarse en consumir esos datos y producir evidencia/reportes.

## Día 5 — Integración, CI y paquete beta 0.5

**Objetivo:** Dejar la beta lista para iterar y mostrar.

- Unificar comandos de setup y smoke en `scripts/`.
- Completar GitHub Actions para backend/frontend/docs.
- Validar que el lab local sube con Docker Compose y que los endpoints fixture responden.
- Añadir decisiones técnicas en `docs/`.
- Pulir README con instrucciones reales.
- Crear checklist beta 0.5.
- Definir qué se migra desde NetVault y qué se descarta.

**Resultado esperado:** Base Lynjax beta 0.5 con estructura, checks y demo reproducible.

## Open Risks

- Aún no existe implementación real de backend ni frontend.
- Docker no está disponible en el shell local actual de Hermes; el lab queda preparado y validado sintácticamente, pero `docker compose up` debe probarse en una máquina con Docker.
- La disponibilidad de nombre/dominio/trademark de Lynjax debe tratarse como provisional hasta verificación externa.
- Migrar código NetVault sin smoke checks previos puede reintroducir deuda; debe hacerse de forma selectiva.
