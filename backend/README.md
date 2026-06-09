# Lynjax Backend beta 0.5

Backend FastAPI aislado para pruebas beta de Lynjax. Los endpoints de evaluación usan resultados simulados y no ejecutan escaneos ni conexiones de red externas.

## Estructura

- `app/main.py`: aplicación FastAPI y registro de routers.
- `app/api/routes/`: endpoints HTTP.
- `app/core/config.py`: configuración base del ambiente beta.
- `app/services/checks/`: checks seguros/simulados.
- `app/schemas/`: modelos Pydantic.
- `tests/`: pruebas de contrato mínimo.

## Crear entorno virtual

Desde la carpeta `backend`:

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash en Windows
# En Linux/macOS: source .venv/bin/activate
```

## Instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Ejecutar API local

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints iniciales:

- `GET /health`
- `GET /api/v1/info`
- `POST /api/v1/assessments/connectivity-demo`

Ejemplo seguro del endpoint demo:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessments/connectivity-demo \
  -H 'Content-Type: application/json' \
  -d '{"hosts":["target-web"],"checks":["http","dns"]}'
```

## Ejecutar tests

Desde la raíz del repo:

```bash
python -m pytest backend/tests -v
```
