# Lynjax Virtualization

Compose beta para levantar backend, frontend y targets demo en un runtime Docker/Linux aislado.

## Uso

```bash
cd virtualization
bash run-beta-compose.sh config
bash run-beta-compose.sh up
```

Abrir:

- Frontend: `http://127.0.0.1:5173/`
- Backend health: `http://127.0.0.1:8000/health`
- Lab web: `http://127.0.0.1:18080/`
- Lab metadata: `http://127.0.0.1:18081/metadata.json`

Apagar:

```bash
bash run-beta-compose.sh down
```

Más detalles:

- `../docs/VIRTUALIZED_ENVIRONMENTS.md`
- `../docs/lab/CONTAINERLAB_PREP.md`
- `containerlab/README.md`

## Containerlab

El subdirectorio `containerlab/` contiene una topología demo sanitizada para inspección visual y futura ejecución dentro de WSL2 Ubuntu/Debian, una VM Ubuntu o CI. No se debe desplegar desde Windows/Git Bash si Docker/Containerlab no están disponibles en una capa Linux aprobada.

Validación estática desde la raíz del repo:

```bash
bash scripts/lab_validate.sh
```
