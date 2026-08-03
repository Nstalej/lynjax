# Rebranding + Reestructuración NetVault → Beta 0.5

## Propósito

Crear una nueva base limpia para evolucionar la idea de NetVault hacia una beta 0.5 estable, escalable y presentable, evitando arrastrar deuda técnica de versiones 0.1/0.2.

## Decisión inicial

- NetVault queda como repositorio/base histórica.
- El nuevo proyecto se trabajará desde cero en una carpeta nueva.
- Se migrará solo lo que esté probado y útil.
- La autenticación se asumirá desde el inicio con JWT/RBAC; no se mantendrán pruebas antiguas que ignoren autenticación.
- El objetivo no es simular una red enterprise completa todavía; primero se estabiliza un análisis base beta reproducible.

## Entorno aislado propuesto

### Opción recomendada para beta 0.5

Usar aislamiento por capas:

1. **Python virtual environment local** para backend y scripts.
2. **Docker Compose** para servicios auxiliares y demo local.
3. **Sin virtualizadores pesados al inicio**: no GNS3, no EVE-NG, no VM dedicada como requisito inicial.
4. **Laboratorio local simulado** con servicios fake: HTTP/TCP/SNMP fake más datos demo.

Esto permite desarrollar y probar sin switches físicos, sin bloquear la laptop y sin depender de hardware externo.

### Por qué no empezar con virtualizador

- GNS3/EVE-NG agregan complejidad antes de estabilizar la app.
- Para análisis base beta basta con targets locales/Docker y pruebas controladas.
- Después, cuando la beta genere reportes y flujos estables, se puede agregar Containerlab/GNS3 como fase 2.

## Qué se necesita

### Mínimo en tu laptop

- Python 3.11 en venv aislado.
- Node.js para frontend.
- Git.
- Docker Desktop opcional pero recomendado para demo/lab.
- Sin switches físicos.
- Sin equipo externo para la primera beta.

### Para pruebas de campo reales

- Autorización explícita del cliente/red.
- Rango IP autorizado.
- Credenciales entregadas por el cliente si se probará SSH/SNMP/API.
- Regla: no escanear fuera del alcance autorizado.

## Propuesta de naming

Criterios:

- Corto: 5–8 letras idealmente.
- Sonido técnico/comercial.
- No tiene que significar algo literal.
- Debe poder verse bien en logo, dashboard, CLI y reportes.
- Evitar nombres genéricos tipo NetVault porque ya existen usos similares.

### Candidatos iniciales

1. **Nodrix** — nodos + sonido técnico fuerte.
2. **Zentrix** — memorable, parecido a marcas enterprise, visualmente fuerte.
3. **Veyronet** — más descriptivo, menos abstracto.
4. **Auvrik** — corto, raro, tecnológico.
5. **Nexora** — moderno, limpio, buen sonido SaaS.
6. **Trivanta** — más institucional/consultoría.
7. **Orbyn** — red/orbita/nodos, corto.
8. **Kavrix** — fuerte, tipo Zabbix/PRTG, abstracto.
9. **Lynqra** — link + aura, moderno.
10. **Sentra** — centralización/monitoreo, pero requiere revisar disponibilidad.

### Recomendación provisional

**Kavrix** como nombre de trabajo para la beta 0.5.

Razones:

- Suena técnico y comercial.
- Es corto y recordable.
- No depende de significado literal.
- Se diferencia de NetVault.
- Funciona bien en frases como:
  - Kavrix Core
  - Kavrix Assessment
  - Kavrix Agent
  - Kavrix Report

Pendiente: búsqueda formal de disponibilidad de nombre, dominio y marcas antes de hacerlo definitivo.

## Estructura propuesta del nuevo proyecto

```text
kavrix/
  backend/
    app/
      api/
      auth/
      core/
      devices/
      assessments/
      reports/
    tests/
      unit/
      integration/
  frontend/
    src/
      app/
      components/
      pages/
      services/
  labs/
    local-demo/
  docs/
    branding/
    architecture/
    field-assessment/
    guides/
    plans/
  scripts/
  data/
    .gitkeep
  reports/
    .gitkeep
```

## Qué se migra desde NetVault

Migrar solo después de verificar:

- Modelos de configuración que sí funcionen.
- Health endpoint y estructura FastAPI básica.
- Smoke script como idea, adaptado al nuevo nombre.
- Componentes frontend si compilan y no dependen de rutas rotas.
- Tests útiles reescritos al nuevo flujo JWT.

No migrar automáticamente:

- Tests que fallan por ignorar JWT/RBAC.
- Código duplicado o experimental.
- Artefactos de cache: `__pycache__`, `.pytest_cache`, `dist` viejo.
- Workflows CI/CD que no estén alineados al nuevo diseño.

## Roadmap beta 0.5

### Fase 1 — Base limpia

- Crear repo/carpeta nueva.
- Crear backend FastAPI mínimo.
- Crear JWT desde el inicio.
- Crear health endpoint.
- Crear tests unitarios/integración mínimos.
- Crear frontend shell mínimo.
- Crear smoke script.

### Fase 2 — Assessment local

- Crear modelo de evaluación.
- Registrar scope autorizado.
- Registrar dispositivos manualmente.
- Ejecutar checks básicos.
- Guardar evidencia.
- Generar reporte Markdown.

### Fase 3 — Demo/lab

- Crear lab local con Docker Compose.
- Servicios fake para HTTP/TCP/SNMP.
- Datos demo reproducibles.

### Fase 4 — Branding visual

- Definir nombre final.
- Crear logo simple SVG.
- Definir paleta.
- Definir dashboard visual.
- Preparar landing/README comercial.

## Principio rector

La beta 0.5 debe ser pequeña, estable y demostrable. Mejor 5 funciones que funcionen bien que 20 incompletas.
