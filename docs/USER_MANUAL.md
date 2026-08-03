# Lynjax v1.0-rc1 — Manual de Usuario

## Propósito

Este manual guía la prueba local de Lynjax v1.0-rc1, un candidato técnico para validar **Intelligent Network Visibility**: ejecutar un assessment demo seguro, revisar evidencia estructurada y preparar reportes sin tocar infraestructura real.

## Público objetivo

- Alejandro como operador/desarrollador de la release candidate.
- Revisores técnicos que quieran probar el flujo local.
- Futuras pruebas internas antes de una beta de campo controlada.

## Antes de empezar

Lynjax v1.0-rc1 es sandbox-first:

- No escanea redes reales.
- No requiere credenciales.
- Usa datos demo y targets locales.
- AD/LLM son módulos visuales planificados/read-only.
- Docker/Containerlab deben ejecutarse solo en WSL2/Ubuntu/VM/CI aprobados.

## Arranque rápido

Desde la raíz del repo:

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
bash scripts/dev-start.sh
```

Abrir en el navegador:

- Plataforma Lynjax: `http://127.0.0.1:5173/`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Flujo de demo recomendado

1. Abrir `http://127.0.0.1:5173/`.
2. Confirmar que el header muestra candidato v1.0 y el shell Lynjax.
3. Probar el selector de idioma ES/EN.
4. Recorrer sidebar:
   - Resumen.
   - Activos.
   - Conectividad.
   - Assessments.
   - Evidencia.
   - Reportes.
   - Topología.
   - Directorio / Active Directory.
   - Inteligencia / LLM.
   - Configuración.
5. En el flujo de assessment/demo segura, ejecutar la acción de demo.
6. Confirmar que los resultados, evidencia y reporte preview provienen del backend.
7. Abrir `http://127.0.0.1:8000/docs` y revisar el endpoint `POST /api/v1/assessments/connectivity-demo`.

## Probar endpoint manualmente

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessments/connectivity-demo \
  -H 'Content-Type: application/json' \
  -d '{"hosts":["target-web","target-metadata"],"checks":["http","dns"]}'
```

Resultado esperado:

- `assessment_id` presente.
- `created_at` presente.
- `overall_status` y `risk_level` definidos.
- `targets`, `checks`, `results` y `evidence_summary` poblados.
- `safety_notice` confirma modo demo/sandbox.
- `report_markdown` contiene el reporte generado.

## Verificar que todo funciona

Con backend y frontend levantados:

```bash
bash scripts/smoke-local.sh
```

Resultado esperado:

- Tests backend pasan.
- `/health` responde OK.
- Frontend compila.
- Frontend responde HTTP.

## Prueba WSL2/Compose opcional

Si Docker/Compose está disponible dentro de WSL2/Ubuntu/VM/CI:

```bash
cd /mnt/c/Users/nesal/Documents/001_Programas/lynjax
bash scripts/lab_validate.sh
cd virtualization
bash run-beta-compose.sh up-detached
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:5173/ >/dev/null
curl -fsS http://127.0.0.1:18080/ >/dev/null
curl -fsS http://127.0.0.1:18081/metadata.json >/dev/null
bash run-beta-compose.sh down -v
```

## Apagar servicios locales

```bash
bash scripts/dev-stop.sh
```

## Qué reportar durante pruebas

Registrar:

- Fecha/hora.
- Entorno: Git Bash, WSL2, VM o CI.
- Comando o pantalla probada.
- Resultado esperado vs real.
- Captura/log si falla.
- Si el error aparece solo en Windows o solo en WSL.

## Limitaciones conocidas

- v1.0-rc1 no es producción ni release final.
- No hay autenticación ni persistencia productiva.
- Los módulos AD/LLM/topología avanzada son placeholders seguros.
- Containerlab aún no se desplegó: falta runtime instalado en WSL2/Ubuntu/VM.
- `npm audit` reporta 2 high por Vite/esbuild; requiere evaluar upgrade mayor en rama separada.
