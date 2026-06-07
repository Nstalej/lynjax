# Lynjax

Lynjax es el rebrand limpio de NetVault: un producto de auditoría, visibilidad, assessment y trazabilidad para redes reales. Esta base no migra NetVault completo; define primero la estructura mínima para construir una beta 0.5 usable y verificable.

## Visión

Convertir evaluaciones de red reales en evidencia técnica clara: descubrimiento controlado, hallazgos priorizados, trazabilidad de checks, reportes accionables y un flujo repetible para campo/lab.

## Módulos previstos

- **Backend (`backend/`)**: API FastAPI para inventario, ejecuciones de checks, evidencias, reportes y autenticación básica de beta.
- **Frontend (`frontend/`)**: aplicación React/Vite para dashboard, flujo de assessment, resultados y generación/descarga de reportes.
- **Documentación (`docs/`)**: roadmap, arquitectura, decisiones técnicas y guías de operación.
- **Marca (`brand/`)**: fundamentos visuales y verbales de Lynjax, tokens, logo, mensajes y aplicaciones.
- **Reportes (`reports/`)**: plantillas, ejemplos sanitizados y salidas generadas por assessments.
- **Lab (`lab/`)**: escenarios locales/Docker para demo y validación sin tocar redes reales.
- **Scripts (`scripts/`)**: automatizaciones de smoke test, setup local, lint y utilidades de desarrollo.
- **CI (`.github/workflows/`)**: GitHub Actions para checks de backend, frontend y documentación.

## Comandos previstos

> Estos comandos son la dirección esperada; se activarán cuando existan los proyectos FastAPI y Vite.

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Local lab
bash scripts/lab_validate.sh
bash scripts/lab_up.sh
bash scripts/lab_smoke.sh
bash scripts/lab_down.sh

# Tests futuros
pytest backend/tests -v
npm test --prefix frontend
```

## Estado Día 1/5

- Estructura base creada.
- Sin migración masiva desde NetVault.
- Repo público inicializado en GitHub: `Nstalej/lynjax`.
- CI base de backend/frontend creado.
- Lab local Docker preparado con fixtures seguros y scripts de validación/arranque/parada.
- Siguiente paso: crear backend ejecutable mínimo y conectar los checks contra los fixtures del lab.
