# Lynjax Beta 0.5 Test Notes

Fecha de intake: 2026-06-11

## Contexto

Alejandro reservó 2026-06-09 y 2026-06-10 para probar Lynjax beta 0.5. Este documento captura la retroalimentación disponible al inicio del sprint v0.6 y separa hallazgos reales de placeholders para completar cuando Alejandro comparta notas adicionales.

## Alejandro's findings / hallazgos reportados

- _Placeholder:_ No hay notas nuevas de Alejandro disponibles en el contexto de esta sesión cron.
- Validación histórica documentada en `docs/BETA_0_5_STATUS.md`: backend tests, frontend build y smoke local pasaron durante preparación beta 0.5.

## Blockers / bloqueadores

- _Placeholder:_ Sin bloqueadores nuevos reportados por Alejandro en esta sesión.
- Riesgo conocido: Docker/Compose no estaba disponible desde Git Bash/Windows; validación completa de Compose debe hacerse en WSL2, VM Ubuntu o CI.
- Riesgo conocido: beta 0.5 usa checks simulados y no debe utilizarse como scanner de producción.

## UX/doc issues / problemas de UX o documentación

- _Placeholder:_ Sin confusiones nuevas reportadas por Alejandro en esta sesión.
- Mejora probable para v0.6: explicar dentro del frontend que el flujo es demo/sanitizado y que los resultados provienen del backend local.
- Mejora probable para v0.6: documentar explícitamente cómo exportar o copiar el reporte markdown generado.

## Environment/setup issues / problemas de ambiente y setup

- _Placeholder:_ Sin problemas nuevos de instalación/arranque reportados por Alejandro en esta sesión.
- Baseline conocido: uso recomendado desde Git Bash/WSL en Windows; sin instalaciones host-level ni cambios de features de Windows durante este sprint automatizado.
- Baseline conocido: Docker/Compose puede no existir en el host actual; se prioriza WSL2/VM/CI para validación de lab virtualizado.

## Next-release requests / solicitudes para la próxima versión

- Conectar frontend al endpoint real `POST /api/v1/assessments/connectivity-demo`.
- Renderizar resultados estructurados devueltos por el backend, no solo mocks.
- Generar reporte markdown desde datos reales de la respuesta demo.
- Mejorar smoke checks para cubrir el flujo end-to-end v0.6.
- Mantener límites seguros: targets demo/locales, sin credenciales reales y sin redes externas.

## Release blockers for v0.6

- Falta implementar flujo frontend → backend → resultados → reporte markdown.
- Falta contrato estable para campos de evidencia, timestamp, estado/riesgo y target/check results.
- Falta validar nuevamente tests/build/lab después de cualquier cambio de código.
- Falta decisión de Alejandro si quiere publicar `v0.6` final o `v0.6-rc1` al cierre del sprint.

## Intake follow-up

Cuando Alejandro comparta notas concretas, agregarlas debajo con formato:

```markdown
### YYYY-MM-DD — Fuente
- Hallazgo:
- Pasos para reproducir:
- Resultado esperado:
- Resultado observado:
- Severidad: blocker | must-fix | defer | question
- Evidencia/localización:
```
