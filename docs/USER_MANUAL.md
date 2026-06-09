# Lynjax Beta 0.5 — Manual de Usuario

## Propósito

Este manual guía una demo local de Lynjax beta 0.5 para validar el concepto de **Intelligent Network Visibility**: convertir un assessment de red en evidencia visual, checks trazables y base de reporte técnico.

## Público objetivo

- Alejandro como operador/desarrollador de la beta.
- Revisores técnicos que quieran ver el flujo sin tocar infraestructura real.
- Futuras pruebas con usuarios internos antes de una beta de campo.

## Antes de empezar

La beta actual es local y segura:

- No escanea redes reales.
- No requiere credenciales.
- Usa datos demo y targets locales.
- La API marca explícitamente `network_access: disabled`.

## Arranque rápido

Desde la raíz del repo:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
bash scripts/dev-start.sh
```

Abrir en el navegador:

- Dashboard: `http://127.0.0.1:5173/`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Flujo de demo recomendado

1. Abrir el dashboard Lynjax.
2. Revisar el hero: marca, propósito y tagline.
3. Revisar tarjetas principales:
   - Activos visibles.
   - Hallazgos priorizados.
   - Evidencias vinculadas.
   - Riesgo crítico.
4. Revisar el panel de assessment.
5. Revisar el mapa de evidencia.
6. Abrir `http://127.0.0.1:8000/docs` y probar el endpoint demo.

## Probar endpoint de assessment simulado

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessments/connectivity-demo \
  -H 'Content-Type: application/json' \
  -d '{"hosts":["target-web","target-metadata"],"checks":["http","dns"]}'
```

Resultado esperado:

- `mode`: `simulation`.
- `network_access`: `disabled`.
- `results`: lista de checks simulados por host.

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

## Usar el lab local opcional

Si Docker/Compose está disponible dentro de WSL2, VM Ubuntu o un ambiente CI:

```bash
bash scripts/lab_validate.sh
bash scripts/lab_up.sh
bash scripts/lab_smoke.sh
bash scripts/lab_down.sh
```

Targets demo:

- `http://127.0.0.1:18080/`
- `http://127.0.0.1:18081/metadata.json`

## Apagar servicios

```bash
bash scripts/dev-stop.sh
```

## Qué reportar durante pruebas

Registrar:

- Fecha/hora de prueba.
- Sistema usado: Git Bash, WSL2, VM o CI.
- Comando ejecutado.
- URL abierta.
- Resultado esperado vs resultado real.
- Captura o log si falla.

## Limitaciones conocidas

- El dashboard todavía usa datos mock para la vista visual.
- El endpoint demo no ejecuta probes reales.
- No hay autenticación.
- No hay persistencia de assessments.
- La plantilla de reporte existe, pero aún no hay generación automática desde la API.
