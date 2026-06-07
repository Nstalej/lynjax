# Lynjax Backend

Backend previsto para Lynjax beta 0.5 usando FastAPI.

## Objetivo

Exponer una API mínima para assessments de red: health check, scopes/targets, ejecuciones de checks, evidencia y datos para reportes.

## Stack previsto

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- Pytest
- Persistencia inicial: JSON o SQLite, a decidir cuando exista el primer flujo beta

## Comandos previstos

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest -v
```

## Primera meta técnica

Crear `GET /health` con test automatizado antes de añadir modelos o persistencia.
