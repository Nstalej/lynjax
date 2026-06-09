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

Más detalles: `../docs/VIRTUALIZED_ENVIRONMENTS.md`.
