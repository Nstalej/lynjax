# Estado y trabajo pendiente

> Escrito el 2026-08-10 para que una sesión nueva arranque sin reconstruir contexto.

## Dónde está el proyecto

`C:\Users\nesal\Documents\001_Programas\lynjax` · repo `Nstalej/lynjax` · rama `main`.
**546 tests, CI verde** en backend, frontend y Docker.

Servidor de pruebas local:

```bash
cd backend
LYNJAX_DATA_DIR=/c/Users/nesal/lynjax-data LYNJAX_NETWORK_POLICY=authorized-targets .venv/Scripts/lynjax.exe serve --port 8080
```

`http://127.0.0.1:8080` · `nstalej@lynjax.local` / `lynjax-pruebas-2026`

## El backend está completo

Los 35 endpoints existen y están probados. No falta ninguno para las pantallas que
pide el usuario:

| Pantalla | Endpoint |
|---|---|
| Dashboard | `GET /api/v1/dashboard` — conteos, salud, agentes, actividad reciente |
| Mapa | `GET /api/v1/topology` — nodos, aristas, notas de cómo conoce cada enlace |
| Devices lista | `GET/POST/DELETE /api/v1/devices` |
| Device detail, pestañas | `GET /api/v1/devices/{id}/data` — system, interfaces, arp, mac, routes |
| Probar / auditar uno | `POST /api/v1/devices/{id}/check`, `/audit` |
| Audits historial | `GET /api/v1/audits`, `GET /api/v1/audits/{id}` |
| Nueva auditoría | `POST /api/v1/audit` |
| Informe | `GET /api/v1/reports/{assessment_id}?fmt=md\|pdf` |
| Traza de cadena | `POST /api/v1/trace/{ip}` |
| Descubrimiento | `POST/GET/DELETE /api/v1/discovery` |
| Agents | `GET/POST/DELETE /api/v1/agents`, `POST /agents/{id}/heartbeat` |
| Credenciales | `GET/POST/DELETE /api/v1/credentials` |
| Logs | `GET /api/v1/logs` |
| Cuentas | `/api/v1/auth/*` |
| Purga total | `POST /api/v1/purge` |

Todo exige token. Roles: `viewer` lee · `operator` alcanza la red · `admin` gestiona cuentas.

## Lo que falta: el frontend

**Se construyó al revés.** Se tomó la cáscara de Lynjax —diez módulos de presentación con
descripciones y estados "planned"— y se cableó a endpoints reales, en vez de partir de
cómo se veía NetVault funcionando. El resultado se lee como folleto, no como consola.

### Estructura correcta

Cinco módulos, los de NetVault:

```
Dashboard · Devices · Agents · Audits · Settings
```

Topology es un **panel del Dashboard**, no una entrada de menú. Reports es una **acción
dentro de Audits**. Fuera: Overview, Assets, Connectivity, Assessments, Evidence,
Directory, Intelligence.

### Requisitos por pantalla

**Login** — centrado en pantalla, con fondo y animación. El actual está a un lado, sin
fondo, y el usuario lo describió como burdo y fuera de contexto profesional. Paleta en
`brand/tokens/lynjax-colors.json`.

**Dashboard** — operativo, sin texto explicativo: mapa de topología, equipos activos por
estado, puntaje de salud, rastro de auditoría reciente. Referencia visual: la primera
captura que envió el usuario.

**Devices** — buscador **arriba y visible**, no abajo. Vista de detalle por dispositivo
con pestañas: Overview · Interfaces · ARP Table · MAC Table · Routes · System. Botones
Test / Refresh / Edit / Delete en la cabecera.

**Audits** — tabla con timestamp, objetivo, tipo, hallazgos, estado y "View Report".
Filtros por tipo y estado. Botón de nueva auditoría global. El informe abre en modal.

**Agents** — lista de agentes registrados con estado y último heartbeat, más el panel de
despliegue con el token. El agente de Windows AD **no está portado** todavía; la pantalla
y el registro sí funcionan.

**Settings** — General, Credenciales (alta y baja) y System Logs.

### Archivos del frontend

`frontend/src/` — `lib/api.ts` ya tiene cliente tipado y sesión. Las páginas actuales
(`AssetsPage`, `AuditPage`, `DiscoveryPage`) se reemplazan. `layout/AppShell.tsx` decide
el enrutado; `components/nav/navItems.ts` define el menú a reducir.

Construir e instalar el bundle dentro del paquete:

```bash
PYTHON=backend/.venv/Scripts/python.exe bash scripts/build-release.sh
```

## Lo que sigue sin estar

- Agente de Windows AD (803 líneas en el respaldo de NetVault). Acordado para después.
- Servidor MCP. Acordado para después.
- Diagramación profesional con LLDP/CDP y vistas BGP/OSPF.
- Frontend sin tests.
- Sin validación contra hardware real: todo se probó con dobles y muestras capturadas.
- Sin rate limiting en el login.

## Respaldo de NetVault

`001_Programas/_archived_workspaces/netvault-final-20260731/` — archivos y mirror git con
12 ramas. El repo `Nstalej/netvault` quedó archivado en GitHub.
