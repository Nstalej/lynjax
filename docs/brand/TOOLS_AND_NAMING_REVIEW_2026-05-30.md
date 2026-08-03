# Revisión de herramientas, repos y naming — 2026-05-30

## Contexto

Alejandro revisó opciones de trabajo remoto y se postuló a una oportunidad. Algunas plataformas no funcionaron o no permitieron completar postulación, especialmente Jobicy por login/opción no habilitada. Queda pendiente esperar la revisión del CV.

También se revisó que varios nombres propuestos para el rebranding de NetVault ya tienen `.com` registrado. Se busca un nombre más distintivo y disponible.

## Acciones realizadas en el entorno local

### Repos clonados para análisis

Ubicación:

```text
C:\Users\nesal\Documents\001_Programas\_research_repos
```

Clonados:

```text
coolify/
ui-ux-pro-max-skill/
impeccable/
agent-skills/
```

### Herramientas instaladas

Se instalaron globalmente con npm:

```bash
npm install -g uipro-cli impeccable
```

Verificado:

```text
uipro: 2.2.3
impeccable: 2.3.2
```

### Skills instaladas en Hermes

Se instalaron correctamente:

```text
web-design-guidelines
deploy-to-vercel
```

Intentos bloqueados por el escáner de seguridad de Hermes:

```text
vercel-react-best-practices
vercel-composition-patterns
vercel-react-view-transitions
```

Motivo: el escáner marcó referencias tipo `AGENTS.md` como persistencia peligrosa. No se forzó ni se hizo bypass. Quedan disponibles clonadas para lectura manual en `_research_repos/agent-skills`, pero no instaladas como skill activa.

## Evaluación de cada recurso

### 1. Coolify

URL: https://github.com/coollabsio/coolify

Conclusión: útil, pero no para instalar ahora en esta PC.

Uso recomendado:

- Futuro panel self-hosted para desplegar proyectos propios.
- Alternativa a Vercel/Netlify si se contrata un VPS.
- Puede servir para hospedar landing personal, dashboard demo o servicios internos.

No recomendado ahora porque:

- Está pensado para servidor Linux/VPS con Docker.
- Instalarlo en Windows local agregaría complejidad.
- Para `Nstalej.com` o landing inicial conviene primero Vercel/Netlify/Cloudflare Pages.

Decisión:

- No instalar Coolify localmente todavía.
- Mantenerlo como opción fase 2 cuando exista VPS.

### 2. UI UX Pro Max Skill

URL: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

Conclusión: sí es funcional para mejorar diseño de landing pages y UI.

Qué aporta:

- Reglas de diseño UI/UX.
- Datos de estilos, tipografía, colores, landing pages y frameworks.
- CLI `uipro-cli` para instalar guías en asistentes de código.

Decisión:

- Instalado globalmente `uipro-cli`.
- Usarlo cuando creemos la landing personal o la nueva landing del producto.
- No ejecutar aún `uipro init` hasta tener el proyecto destino creado.

Comando futuro por proyecto:

```bash
cd C:/Users/nesal/Documents/001_Programas/nstalej-landing
uipro init --ai codex
```

O para otro asistente compatible:

```bash
uipro init --ai opencode
uipro init --ai cursor
uipro init --ai all
```

### 3. Impeccable

URL: https://github.com/pbakaus/impeccable

Conclusión: muy útil para diseño serio de frontend, auditoría visual y evitar diseños genéricos de IA.

Qué aporta:

- Skill de diseño frontend.
- Anti-pattern detector.
- Comandos para auditar/pulir UI.
- Reglas de tipografía, color, motion, responsive y UX writing.

Decisión:

- Instalado globalmente `impeccable`.
- Usarlo para auditar landing personal, landing del producto y dashboard.

Comandos útiles:

```bash
impeccable --version
npx impeccable detect src/
npx impeccable detect index.html
npx impeccable detect https://example.com
```

### 4. Vercel Agent Skills

URL: https://github.com/vercel-labs/agent-skills

Conclusión: parcialmente útil.

Instaladas:

- `web-design-guidelines`: para revisar accesibilidad, UX y buenas prácticas web.
- `deploy-to-vercel`: para guiar despliegues preview/producción en Vercel.

No instaladas por seguridad:

- React best practices.
- Composition patterns.
- React view transitions.

Aun así, el repo clonado se puede consultar manualmente.

Uso recomendado:

- Para `Nstalej.com`: deploy inicial en Vercel o Cloudflare Pages.
- Para nueva landing del producto: revisión de UI antes de publicar.

### 5. MCPMarket React Native Skills

URL: https://mcpmarket.com/es/tools/skills/react-native-skills

Resultado: la página devolvió HTTP 429 durante la consulta automatizada. Sin embargo, el repo `vercel-labs/agent-skills` incluye `react-native-skills`.

Conclusión:

- No es prioritario para NetVault/Kavrix si empezamos web dashboard.
- Útil solo si después creamos app móvil con React Native/Expo.

Decisión:

- No instalar ahora.
- Mantener como referencia futura.

### 6. Remotion

URL: https://www.remotion.dev/

Conclusión: útil para marketing, no para la base técnica inmediata.

Qué permite:

- Crear videos programáticamente con React.
- Generar MP4s para demos, intros, visualizaciones o contenido comercial.
- Automatizar videos a partir de datos.

Uso potencial:

- Video corto para presentar la evolución NetVault → nuevo producto.
- Demo animada del dashboard.
- Contenido para portfolio `Nstalej.com`.
- Explicadores técnicos animados.

No instalar todavía porque:

- Se debe instalar dentro de un proyecto específico.
- No aporta a estabilizar backend/JWT/reportes.

Comando futuro:

```bash
npm create video@latest
```

## Naming — nuevas opciones

### Resultado de comprobación rápida

Se hizo una comprobación técnica básica con RDAP/DNS. Esto no reemplaza una búsqueda formal en registrador ni búsqueda de marca, pero ayuda a filtrar.

Candidatos con señal de posible disponibilidad por DNS/RDAP:

```text
Axonvy.com
Orqiva.com
Vantyx.com
Nodvanta.com
Netrivio.com
Kavrova.com
Rynovaq.com
Obryxio.com
Nodvex.com
Veloraq.com
Kavlynx.com
Orvynx.com
Vantoryx.com
Zyvara.com
Elyvra.com
Nstalyx.com
Nstalej.com
```

Candidatos que resolvieron DNS o aparecieron registrados/no claros:

```text
Nexoryn.com
Vyrnex.com
Orvanta.com
Kavoryx.com
Nodara.com
Veyrion.com
Roventis.com
Lynvora.com
Qavrix.com
Nerviq.com
Veyrix.com
Novyra.com
Zentavo.com
Kaventa.com
Auvyra.com
Nexavox.com
Axyvra.com
Novyrix.com
Kovanta.com
```

## Shortlist recomendada

### Para el producto tipo NetVault/Kavrix

1. **Kavlynx**
   - Fuerte para redes.
   - Combina sonido técnico con `lynx/link`.
   - Buen potencial visual para logo.

2. **Nodvex**
   - Evoca nodos + vector/vertex.
   - Corto y técnico.

3. **Orvynx**
   - Abstracto, comercial, con sonido enterprise.
   - Puede funcionar bien en logo oscuro.

4. **Vantyx**
   - Sonido fuerte, tipo SaaS/infra.
   - Menos explícito, más marca.

5. **Netrivio**
   - Más descriptivo de red.
   - Menos abstracto, más fácil de asociar.

### Para marca personal/portfolio

1. **Nstalej.com**
   - Muy recomendable para marca personal porque es único y ya conecta con tu identidad.
   - Ideal para portfolio, proyectos, CV, blog técnico y demos.

2. **Nstalyx.com**
   - Variante más comercial/tech, pero menos personal.

## Recomendación estratégica

Separar dominios:

```text
Nstalej.com        → marca personal / portfolio / proyectos / CV / blog técnico
NombreProducto.com → producto rebrand de NetVault
```

Esto evita mezclar tu identidad profesional con un producto que todavía puede cambiar de nombre.

## Propuesta de stack para landing personal

Para `Nstalej.com`:

```text
Next.js o Astro
Tailwind CSS
Vercel o Cloudflare Pages
Dominio en Hostinger apuntando por DNS
Secciones:
  - Hero profesional
  - Proyectos destacados
  - NetVault/rebrand como caso de estudio
  - Automatización/AI workflows
  - CV descargable
  - Contacto
```

## Propuesta de stack para landing del producto

Para el rebrand de NetVault:

```text
Next.js o Vite React
Tailwind CSS
Framer Motion o CSS animations ligeras
Dashboard demo visual
Logo SVG propio
Deploy preview en Vercel
```

## Próximo paso recomendado

1. Comprar o reservar `Nstalej.com` si aparece disponible en Hostinger.
2. Elegir 3 finalistas para el producto:
   - Kavlynx
   - Nodvex
   - Orvynx
3. Verificar esos 3 en Hostinger + búsqueda rápida de GitHub/npm/marca.
4. Crear proyecto:

```text
C:\Users\nesal\Documents\001_Programas\nstalej-landing
```

5. Crear proyecto separado del producto cuando definamos nombre:

```text
C:\Users\nesal\Documents\001_Programas\kavlynx
```

O el nombre elegido.
