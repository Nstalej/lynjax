# Lynjax Architecture — Beta 0.5

## Objetivo beta 0.5

Lynjax beta 0.5 debe demostrar un flujo completo y estrecho: definir un assessment autorizado, ejecutar o simular checks controlados, conservar evidencia trazable y entregar un reporte claro. La prioridad es repetibilidad y claridad, no amplitud de features.

## Principios

- **No migración masiva:** NetVault es referencia histórica; solo se migran piezas verificadas y necesarias.
- **Campo primero, lab seguro:** diseñar pensando en redes reales, validar primero en escenarios locales/Docker.
- **Trazabilidad:** cada hallazgo debe poder apuntar a check, target, timestamp y evidencia.
- **DRY/YAGNI:** construir solo lo necesario para la beta.
- **Separación clara:** API, UI, reportes, lab y marca viven en carpetas separadas.

## Vista de alto nivel

```text
+-------------------+        +--------------------+        +-------------------+
| React/Vite UI     |  HTTP  | FastAPI Backend    |  FS/DB | Evidence/Reports  |
| frontend/         +------->| backend/           +------->| reports/          |
+-------------------+        +---------+----------+        +-------------------+
                                      |
                                      | scripts / fixtures
                                      v
                              +--------------------+
                              | Local Lab          |
                              | lab/ + scripts/    |
                              +--------------------+
```

## Componentes

### Backend — `backend/`

Responsabilidades previstas:

- API HTTP con FastAPI.
- Health check y metadata de versión.
- Gestión de assessments.
- Registro de targets dentro de un scope autorizado.
- Registro de ejecuciones de checks.
- Persistencia inicial simple: JSON/SQLite según la necesidad del Día 2-4.
- Generación o preparación de datos para reportes.

Módulos futuros sugeridos:

```text
backend/
  app/
    main.py
    api/
    core/
    models/
    services/
    schemas/
  tests/
  requirements.txt
```

### Frontend — `frontend/`

Responsabilidades previstas:

- Dashboard de estado de assessment.
- Vista de targets y checks.
- Vista de hallazgos/evidencia.
- Enlace o acción para reporte.
- Demo presentable con datos mock mientras el backend madura.

Módulos futuros sugeridos:

```text
frontend/
  src/
    App.tsx
    components/
    pages/
    lib/
  package.json
  vite.config.ts
```

### Docs — `docs/`

Responsabilidades:

- Roadmap.
- Arquitectura.
- Decisiones técnicas.
- Guías operativas de campo/lab.
- Checklists de beta.

### Brand — `brand/`

Responsabilidades:

- Identidad visual/verbal Lynjax.
- Tokens y criterios de diseño.
- Mensajes: auditoría, visibilidad, assessment, trazabilidad.
- Referencias migradas selectivamente desde `brand-kit-minimum/` solo cuando encajen.

### Reports — `reports/`

Responsabilidades:

- Plantillas de reporte.
- Ejemplos sanitizados.
- Salidas generadas localmente.

Regla: evitar commitear reportes reales de clientes o datos sensibles.

### Lab — `lab/`

Responsabilidades:

- Escenarios locales o Docker Compose.
- Fixtures de targets seguros.
- Datos mock para demostrar el flujo sin hardware ni redes externas.

### Scripts — `scripts/`

Responsabilidades:

- Setup local.
- Smoke checks.
- Validaciones repetibles.
- Automatización simple, sin ocultar pasos críticos.

### GitHub Actions — `.github/workflows/`

Responsabilidades previstas:

- Validar backend.
- Validar frontend.
- Validar documentación y estructura.

## Flujo beta previsto

1. Definir assessment y scope autorizado.
2. Registrar targets dentro del scope.
3. Ejecutar checks seguros o usar fixtures de lab.
4. Guardar resultados y evidencia con timestamps.
5. Mostrar resumen en UI.
6. Generar reporte markdown/JSON/PDF futuro.
7. Purgar datos sensibles cuando aplique.

## Límites explícitos

- No ejecutar scans agresivos por defecto.
- No integrar credenciales reales hasta tener flujo de autorización y secret handling.
- No migrar todo NetVault automáticamente.
- No añadir GNS3/EVE-NG/VMs complejas antes de tener demo local estable.
