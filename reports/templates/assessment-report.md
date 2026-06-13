# Lynjax Assessment Report

> Plantilla técnica base para candidato v1.0. No incluir credenciales, secretos, datos personales ni evidencia de clientes reales sin sanitización. El flujo demo actual renderiza Markdown desde la respuesta estructurada de `/api/v1/assessments/connectivity-demo`.

## 1. Resumen Ejecutivo

- **Cliente / Entorno:** `<nombre del cliente o lab>`
- **Fecha:** `<YYYY-MM-DD>`
- **Consultor:** Alejandro / Lynjax
- **Estado general:** `<Aprobado con observaciones | Requiere atención | Crítico>`
- **Conclusión breve:** `<2-4 líneas sobre exposición, hallazgos prioritarios y siguiente acción>`

## 2. Alcance Autorizado

| Elemento | Valor |
| --- | --- |
| Ventana de assessment | `<fecha/hora inicio - fin>` |
| Redes / hosts autorizados | `<CIDR, hostnames o fixtures lab>` |
| Exclusiones | `<sistemas fuera de alcance>` |
| Modo de ejecución | `<lab | campo | simulación>` |
| Contacto de autorización | `<nombre / rol>` |

## 3. Metodología Lynjax

1. Confirmación de alcance y reglas de ejecución.
2. Descubrimiento controlado de activos visibles.
3. Checks seguros de conectividad/servicio dentro del alcance.
4. Normalización de evidencia técnica.
5. Priorización de hallazgos por impacto y probabilidad.
6. Recomendaciones accionables y trazables.

## 4. Inventario de Activos Observados

| ID | Activo | Tipo | Evidencia | Estado |
| --- | --- | --- | --- | --- |
| `AST-001` | `<host>` | `<web | gateway | switch | servicio>` | `<archivo, captura o endpoint>` | `<ok | revisar>` |

## 5. Hallazgos Priorizados

### FND-001 — `<Título del hallazgo>`

- **Severidad:** `<Crítica | Alta | Media | Baja | Informativa>`
- **Activo(s):** `<AST-001>`
- **Descripción:** `<qué se observó y por qué importa>`
- **Evidencia:** `<referencia a captura/log/check>`
- **Impacto potencial:** `<riesgo técnico o de negocio>`
- **Recomendación:** `<acción concreta, verificable>`
- **Validación posterior:** `<cómo confirmar que se corrigió>`

## 6. Evidencia Técnica

| Evidencia | Fuente | Timestamp | Hash / Referencia | Notas |
| --- | --- | --- | --- | --- |
| `EVD-001` | `<endpoint/check>` | `<ISO-8601>` | `<sha256 si aplica>` | `<sanitizado>` |

## 7. Limitaciones

- El assessment cubre únicamente el alcance autorizado.
- La beta 0.5 usa checks simulados o controlados por defecto.
- No se ejecutan scans agresivos ni pruebas intrusivas sin aprobación explícita.
- La ausencia de hallazgos no equivale a ausencia total de riesgo.

## 8. Plan de Remediación Sugerido

| Prioridad | Acción | Responsable | Plazo sugerido | Criterio de cierre |
| --- | --- | --- | --- | --- |
| P1 | `<acción inmediata>` | `<equipo>` | `<fecha>` | `<evidencia esperada>` |

## 9. Apéndice: Comandos / Checks Ejecutados

```bash
# Ejemplos beta/lab
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:18080/
curl -fsS http://127.0.0.1:18081/metadata.json
```

## 10. Purga y Manejo de Datos

- **Datos sensibles removidos:** `<sí/no>`
- **Ubicación de evidencia local:** `<ruta>`
- **Fecha recomendada de purga:** `<YYYY-MM-DD>`
- **Aprobación de retención:** `<responsable>`
