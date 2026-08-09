# Lynjax

**Intelligent Network Visibility, Audit & Traceability**

Lynjax conecta a una red autorizada, recorre los equipos, y responde la pregunta
que un técnico tiene enfrente: *"esta computadora está lenta — ¿dónde está el
problema?"*. Sigue la cadena desde el endpoint, pasando por el cableado y el
switch de acceso, hasta el core y el firewall, y señala en qué eslabón falla.

El entregable es un informe en PDF que se puede entregar a un cliente sin
editarlo.

---

## Seguridad primero

Lynjax alcanza infraestructura real. Dos cosas antes de nada:

**El acceso real a la red está apagado por defecto.** Ninguna operación que abra
un socket funciona hasta que lo habilites explícitamente:

```bash
export LYNJAX_NETWORK_POLICY=authorized-targets
```

Actívalo **solo** para una red que tengas autorización escrita de evaluar. Sin
esa variable, la API responde `403` con el motivo, y eso es correcto: no es una
falla, es la herramienta haciendo lo que se le configuró.

**El descubrimiento rechaza lo que casi siempre es un error.** El alcance se
limita a un máximo de direcciones, así que un `10.0.0.0/8` mal tecleado se
rechaza en vez de lanzar dieciséis millones de sondeos. El espacio de
direcciones público se rechaza salvo que lo habilites aparte.

---

## Instalación

Un solo paquete, tres formas de usarlo. El frontend compilado viaja dentro del
paquete Python, así que no hay servidor web aparte que configurar.

### Laptop de campo — Windows, Linux o macOS

```bash
pipx install lynjax
lynjax init
lynjax serve
```

Abre `http://127.0.0.1:8080`. `lynjax init` genera las claves en el primer
arranque; no hay que editar ningún archivo a mano.

Para el informe en PDF:

```bash
pipx install "lynjax[pdf]"
```

### Servidor

```bash
docker compose up -d
```

Un contenedor, un puerto. Los datos persisten en el volumen `lynjax-data`.

### Sin interfaz, para automatizar

```bash
lynjax audit --client "Nombre del cliente" --out informe.pdf
```

---

## Comandos

| Comando | Qué hace |
|---|---|
| `lynjax init` | Genera claves, crea la base de datos y muestra dónde queda todo |
| `lynjax serve` | Levanta la API y la interfaz en un puerto |
| `lynjax audit` | Auditoría headless que escribe el informe |
| `lynjax purge --yes` | Borra dispositivos y credenciales tras una visita |
| `lynjax info` | Rutas, política activa y conectores disponibles |

`lynjax audit --trace 10.0.0.50` incluye la traza de cadena de ese endpoint en
el informe.

---

## Qué hace

**Conectores.** SSH (RouterOS y Cisco IOS), SNMP v2c y v3, y REST (Sophos XG/XGS
y APIs JSON configurables).

**Auditoría entre equipos.** IPs duplicadas, MAC aprendidos en varios puertos,
hosts activos que no están en el inventario, y puertos con errores.

**Traza de cadena.** Dada la IP de un endpoint: resuelve su MAC por ARP,
encuentra el switch y el puerto donde está aprendido, juzga ese puerto por sus
contadores, y sigue las rutas por defecto hasta el borde. Un puerto caído,
errores que apuntan a cableado, o un enlace gigabit negociado a 100 Mbps
aparecen como el titular del diagnóstico.

**Descubrimiento.** Escaneo de un alcance autorizado con progreso en vivo.

**Informe.** Markdown y PDF, en español o inglés, con una sección explícita de
lo que **no** se pudo cubrir.

---

## Configuración

Todas las variables usan el prefijo `LYNJAX_`.

| Variable | Por defecto | Para qué |
|---|---|---|
| `LYNJAX_NETWORK_POLICY` | `simulated-checks-only` | `authorized-targets` habilita el acceso real |
| `LYNJAX_HOST` | `127.0.0.1` | Dirección de escucha |
| `LYNJAX_PORT` | `8080` | Puerto |
| `LYNJAX_DATA_DIR` | según el sistema operativo | Base de datos, claves |
| `LYNJAX_LOG_LEVEL` | `INFO` | Nivel de log |
| `LYNJAX_CREDENTIALS_MASTER_KEY` | se genera sola | Clave del vault de credenciales |

> **Respalda el archivo de secretos.** Perder `LYNJAX_CREDENTIALS_MASTER_KEY`
> hace que las credenciales guardadas no se puedan recuperar. `lynjax init` te
> dice dónde queda.

---

## Trabajo de campo

1. Confirma la autorización **por escrito**, incluyendo el rango de direcciones.
2. Conecta a la red y registra el alcance autorizado.
3. Guarda las credenciales que te dieron: `lynjax` las cifra en reposo.
4. Habilita `LYNJAX_NETWORK_POLICY=authorized-targets`.
5. Ejecuta la auditoría y valida los hallazgos con el cliente.
6. Entrega el informe.
7. **Purga los datos del cliente**: `lynjax purge --yes`.

El paso 7 no es opcional. Las credenciales de un cliente no deben quedarse en tu
laptop después de la visita.

---

## Desarrollo

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest

cd ../frontend
npm ci
npm run dev
```

Datos de ejemplo, con direcciones RFC 5737 que no están enrutadas a ningún lado:

```bash
python backend/scripts/seed_demo.py
```

---

## Estado

**v0.6 en desarrollo hacia v1.0.** Funcionalidad completa de auditoría de red,
conectores, descubrimiento, traza de cadena, empaquetado e informes.

Planeado para **v1.5**: agente de Active Directory, servidor MCP para consultas
en lenguaje natural, y diagramación de red profesional.

Lynjax es la continuación de NetVault, que quedó archivado por conflicto de
marca. El motor viene de ahí; la estructura, el nombre y las protecciones son
nuevas.

---

## Licencia

MIT — ver [LICENSE](LICENSE).
