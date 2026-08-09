# Guía de auditoría de campo

Procedimiento para usar Lynjax en la red de un cliente. Está escrito como una
lista que se sigue en orden, porque en sitio se olvidan cosas.

---

## Antes de conectar

### Autorización por escrito

**No conectes Lynjax a una red que no tengas permiso de evaluar.** Un escaneo no
autorizado es, en muchas jurisdicciones, un delito — y en todas es motivo
suficiente para perder el contrato.

Lo mínimo que debe decir la autorización:

- [ ] Quién autoriza, con cargo y capacidad para hacerlo.
- [ ] **Los rangos de direcciones exactos** que se pueden evaluar.
- [ ] Fecha y ventana horaria.
- [ ] Qué queda explícitamente fuera de alcance.
- [ ] Qué se hará con las credenciales al terminar.

Un correo del responsable de TI aprobando el alcance sirve. Un "sí, dale" verbal
en el pasillo no.

### Qué pedir al cliente

- [ ] Rangos de las VLAN o subredes a evaluar.
- [ ] Credenciales de **solo lectura** para los equipos de red. Si te ofrecen
      credenciales de administrador, pide de lectura: no las necesitas y su
      custodia es un riesgo que no te conviene aceptar.
- [ ] Comunidad SNMP, si quieren descubrimiento por SNMP.
- [ ] La IP o el nombre de los equipos de los que se están quejando.

---

## En sitio

### 1. Preparar

```bash
lynjax init
lynjax info
```

Confirma la ruta de datos y que la política diga `simulated-checks-only`.

### 2. Registrar el alcance

Registra los equipos y sus credenciales desde la interfaz (módulo **Assets**) o
con la API. Las credenciales quedan cifradas en reposo con la clave que generó
`lynjax init`.

### 3. Habilitar el acceso real

Solo ahora, y solo si tienes el paso de autorización cerrado:

```bash
export LYNJAX_NETWORK_POLICY=authorized-targets
```

En Windows PowerShell:

```powershell
$env:LYNJAX_NETWORK_POLICY = "authorized-targets"
```

### 4. Descubrimiento, si aplica

Limita el alcance a lo autorizado. Lynjax rechaza rangos mayores al tope y el
espacio público, pero **el tope no sustituye tu criterio**: que acepte un
`/24` no significa que ese `/24` esté en tu autorización.

### 5. Auditar

```bash
lynjax audit --client "Nombre del cliente" --locale es --out informe.pdf
```

Para el caso concreto de un equipo lento, agrega la traza:

```bash
lynjax audit --client "Cliente" --trace 10.0.0.50 --out informe.pdf
```

### 6. Validar con el cliente

Antes de entregar, revisa los hallazgos con quien conoce la red. Lynjax reporta
lo que observó; el contexto lo pone el cliente. Una IP duplicada puede ser un
error real o dos interfaces de un cluster que ellos conocen.

Presta atención a la sección **Alcance no cubierto**: un equipo no alcanzado no
es un equipo sano, y conviene decirlo en voz alta.

### 7. Purgar

```bash
lynjax purge --yes
```

**Este paso no es opcional.** Borra los dispositivos y las credenciales del
cliente de tu laptop. Hazlo antes de salir del sitio, no "después".

Verifica:

```bash
lynjax info
```

---

## Qué reporta Lynjax y qué no

**Sí:**

- IPs duplicadas y MAC aprendidos en varios puertos.
- Puertos con errores de entrada significativos.
- Enlaces negociados por debajo de su capacidad.
- Hosts activos que no están en el inventario.
- La cadena entre un endpoint y el borde, con el eslabón problemático.
- Exposición de SNMP: v2c en claro, comunidades por defecto.
- APIs de gestión sin TLS o con verificación de certificado desactivada.

**No, todavía:**

- Nada de Active Directory ni de usuarios. Está planeado para v1.5.
- Nada dentro del endpoint: procesos, disco, memoria.
- Análisis de tráfico o captura de paquetes.
- Adyacencias BGP u OSPF.

Decirle al cliente lo que la herramienta **no** miró es parte del trabajo. Un
informe que solo enumera lo que salió bien se lee como una garantía que nadie
puede dar.

---

## Notas de seguridad

- Lynjax **nunca adivina credenciales.** El descubrimiento por SNMP se omite si
  no le das una comunidad, en lugar de probar las comunes: eso sería fuerza
  bruta, no descubrimiento.
- Las claves de host SSH desconocidas se rechazan por defecto. Aceptarlas exige
  activarlo a propósito y desactiva la protección contra intermediarios.
- Todo lo que hace Lynjax es de **solo lectura**. No modifica configuración de
  ningún equipo.
- El archivo de secretos guarda la clave maestra del vault. Trátalo como una
  credencial: respáldalo, y no lo dejes en un repositorio ni en un disco
  compartido.
