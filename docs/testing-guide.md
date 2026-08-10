# Manual de pruebas de Lynjax

Guía paso a paso para instalar Lynjax en otra máquina, validarlo, y reportar
fallos de forma que se puedan arreglar.

> **Versión probada:** 0.6.0-dev · **Fecha:** 2026-08-10
> **Estado:** los artefactos existen pero **no están publicados en PyPI**. Se
> copian a mano, como se explica abajo.

---

## 1. De dónde sacar el producto

### Repositorio

`https://github.com/Nstalej/lynjax` — rama `main`.

### Los instaladores

No hay descarga pública. Los artefactos se construyen en esta máquina y viven en:

```
C:\Users\nesal\Documents\001_Programas\lynjax\backend\dist\
    lynjax-0.6.0.dev0-py3-none-any.whl     (~166 KB, incluye la interfaz web)
    lynjax-0.6.0.dev0.tar.gz               (~191 KB, código fuente)
```

El `.whl` es el instalador. **Copia ese archivo** a la máquina de prueba: USB,
carpeta compartida, o lo que uses.

### Reconstruirlos

Si cambia el código, hay que reconstruirlos:

```bash
cd C:\Users\nesal\Documents\001_Programas\lynjax\frontend
npm run build

cd ..\backend
rmdir /s /q lynjax\web
xcopy /E /I ..\frontend\dist lynjax\web
.venv\Scripts\python.exe -m build
```

El paso del `xcopy` **no es opcional**: mete la interfaz compilada dentro del
paquete. Sin él, el wheel instala una API sin interfaz.

---

## 2. Requisitos de la máquina de prueba

- **Python 3.11 o 3.12.** Verifica con `python --version`.
- Nada más. Sin Docker, sin Node, sin base de datos.

Para el escenario de servidor hace falta Docker.

---

## 3. Instalación paso a paso (Windows)

### Opción A — pipx (recomendado, aísla la aplicación)

```bat
python -m pip install --user pipx
python -m pipx ensurepath
```

Cierra y reabre la terminal, luego:

```bat
pipx install "C:\ruta\donde\copiaste\lynjax-0.6.0.dev0-py3-none-any.whl[pdf]"
```

### Opción B — entorno virtual

```bat
python -m venv C:\lynjax\venv
C:\lynjax\venv\Scripts\python.exe -m pip install "C:\ruta\lynjax-0.6.0.dev0-py3-none-any.whl[pdf]"
```

El comando queda en `C:\lynjax\venv\Scripts\lynjax.exe`.

> **Gotcha real de Windows:** si la ruta de instalación es muy larga, `pip`
> falla con `No such file or directory` sobre un archivo de `lxml`. Es el
> límite MAX_PATH de 260 caracteres. **Instala en una ruta corta**, como
> `C:\lynjax`. Me pasó durante estas pruebas.

### Linux o macOS

```bash
pipx install "./lynjax-0.6.0.dev0-py3-none-any.whl[pdf]"
```

---

## 4. Primer arranque

```bat
lynjax --version
lynjax init
lynjax user tu@correo.com --admin
lynjax serve
```

`lynjax user` pide la contraseña de forma interactiva si no pasas `--password`,
que es lo preferible: así no queda en el historial del shell.

**La contraseña debe tener 12 caracteres o más** y no estar en la lista de
contraseñas obvias.

Abre `http://127.0.0.1:8080` e inicia sesión.

---

## 5. Lista de verificación de instalación

Marca cada punto. Si alguno falla, salta a la sección 9.

| # | Comprobación | Resultado esperado |
|---|---|---|
| 1 | `lynjax --version` | `lynjax 0.6.0-dev` |
| 2 | `lynjax init` | Muestra rutas y dice que faltan cuentas |
| 3 | `lynjax info` | `Connectors: rest, rest_api, snmp, ssh` — **los cuatro** |
| 4 | `lynjax info` | `Frontend:` apunta a una ruta dentro de `site-packages` |
| 5 | `lynjax user ... --admin` | `Created ... with role admin` |
| 6 | Repetir el mismo correo | Falla con "already exists" |
| 7 | Contraseña `password123` | Rechazada por la política |
| 8 | `lynjax serve` | Arranca y avisa que el acceso a red está apagado |
| 9 | `http://127.0.0.1:8080` | Pantalla de inicio de sesión |
| 10 | Login con la cuenta creada | Entra al panel |
| 11 | Login con contraseña mala | "Incorrect email or password" |
| 12 | `http://127.0.0.1:8080/docs` | Documentación interactiva de la API |

### Verificación de las barreras de seguridad

Estas son las que más me importan. Con el servidor corriendo, en otra terminal:

```bat
curl -s -o nul -w "%%{http_code}\n" http://127.0.0.1:8080/api/v1/devices
```
**Esperado: `401`.** Sin token no se entra a nada.

En la interfaz, ve a *Assessments* y ejecuta una auditoría.
**Esperado:** un aviso azul explicando que el acceso real a red está
desactivado — **no** un error rojo.

Ahora crea un archivo `.env` en la carpeta desde donde lanzas `lynjax`, con:

```
NETWORK_POLICY=authorized-targets
```

Reinicia `lynjax serve`. **Esperado: sigue apagado.** Si se activa, es un fallo
grave y hay que reportarlo de inmediato.

---

## 6. Prueba con equipos reales

### Con el laboratorio de containerlab (WSL2)

Ya tienes `~/labs/lab-redes` con FRR y SR Linux. Los routers FRR hablan SSH, así
que sirven de objetivo real.

```bash
wsl -d Ubuntu -u root
cd ~/labs/lab-redes
containerlab inspect
```

Anota las IP de gestión de `r1` y `r2`. Luego, desde Lynjax:

1. Registra `r1` con conector **ssh**, tipo **auto**.
2. Guarda la credencial del contenedor FRR.
3. Habilita el acceso real:

```bash
export LYNJAX_NETWORK_POLICY=authorized-targets
lynjax serve
```

4. Pulsa **Probar** en el dispositivo. Debe reportar latencia o un error claro.
5. Ejecuta una auditoría y descarga el PDF.

> Recuerda los gotchas de esa máquina: WSL2 apaga la VM al cerrar la última
> sesión y se pierden los contenedores; hay que mantener una sesión abierta y
> redesplegar con `--reconfigure` tras un reinicio.

### Con tu red física

Tus APs Ruckus en `192.168.1.0/24` responden SSH y probablemente SNMP.

**Antes de escanear tu propia red, ten claro que es tuya.** El descubrimiento
abre conexiones a cada dirección del rango.

```
Descubrimiento → Subredes: 192.168.1.0/24
```

Verifica que aparecen los equipos que conoces y que el indicio de fabricante
tiene sentido.

---

## 7. Escenario Docker

```bash
cd C:\Users\nesal\Documents\001_Programas\lynjax
docker compose up -d --build
docker compose logs -f
```

Luego:

```bash
docker compose exec lynjax lynjax user admin@ejemplo.com --admin
```

Abre `http://localhost:8080`.

**Comprobar:** los datos sobreviven a `docker compose restart` (viven en el
volumen `lynjax-data`), y la política de red sigue apagada salvo que la pases
por `environment` en el compose.

---

## 8. Qué probar en la interfaz

Cosas concretas, no "a ver si funciona":

**Inventario**
- Registrar un dispositivo con cada tipo de conector.
- Registrar dos con el mismo nombre → debe rechazarlo.
- Puerto 70000 → debe rechazarlo.
- Borrar un dispositivo.
- Un dispositivo SSH sin credencial → al probar debe decir que falta.

**Auditoría**
- Ejecutar sin dispositivos → resultado vacío, no un error.
- Descargar el PDF → debe abrir en un lector de PDF.
- Descargar el Markdown.
- Verificar que el informe lista lo **no** cubierto.

**Traza de cadena**
- Con una IP que no existe → debe decir que no se pudo localizar, no fingir éxito.

**Sesión**
- Cerrar sesión y volver a entrar.
- Cerrar el navegador y reabrir → debe pedir sesión otra vez (es a propósito).

**Interfaz en general**
- Redimensionar a ancho de móvil.
- Refrescar la página estando en una sección → debe seguir en la aplicación, no
  dar 404.

---

## 9. Cómo reportar un fallo

Para que sea arreglable, necesito:

1. **Qué hiciste**, paso a paso, para llegar ahí.
2. **Qué esperabas** y **qué pasó**.
3. **Sistema operativo y versión de Python** (`python --version`).
4. **Cómo instalaste**: pipx, venv o Docker.
5. **La salida de `lynjax info`.**
6. Si es de la API: el código de estado y el cuerpo de la respuesta.
7. Si es de la interfaz: abre las herramientas de desarrollo con `F12`, pestaña
   **Console** y **Network**, y copia lo que salga en rojo.
8. Si el servidor falla: la salida de la terminal donde corre `lynjax serve`.

Los logs quedan en la ruta que reporta `lynjax info`.

**No incluyas credenciales reales de un cliente en un reporte.**

---

## 10. Limpiar después de probar

```bat
lynjax purge --yes
```

Borra dispositivos y credenciales. Para dejar la máquina como estaba:

```bat
pipx uninstall lynjax
```

Y borra a mano el directorio de datos que reporta `lynjax info`.

---

## 11. Lo que ya sé que falta

Para que no pierdas tiempo reportándolo:

- **Sin límite de intentos en el login.** Se puede probar contraseñas sin freno.
- **Los informes viven en memoria.** Reiniciar el servidor pierde los generados;
  hay que volver a ejecutar la auditoría.
- **Sin tests de interfaz.** El frontend no tiene pruebas automatizadas; por eso
  tus pruebas manuales valen tanto aquí.
- **Sin Active Directory ni MCP.** Van en v1.5.
- **Sin diagramas de topología.** También v1.5.
- **Nunca se ha probado contra un MikroTik o Cisco físico.** Los parsers se
  validaron con salida capturada, no con hardware en vivo. Esta es la
  incógnita más grande y es donde tus pruebas aportan más.
