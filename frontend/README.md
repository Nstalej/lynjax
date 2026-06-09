# Lynjax Frontend

Frontend React/Vite para la demo visual de **Lynjax - Intelligent Network Visibility**.

## Estructura

```text
frontend/
├── index.html
├── package.json
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   └── DashboardCards.tsx
│   ├── lib/
│   │   └── brand.ts
│   ├── pages/
│   │   └── LynjaxDashboard.tsx
│   └── styles/
│       └── global.css
└── vite.config.ts
```

## Crear desde cero con npm create

Si necesitas recrear el proyecto Vite en otra carpeta:

```bash
npm create vite@latest lynjax-frontend -- --template react-ts
cd lynjax-frontend
npm install
npm run dev
```

## Comandos locales

```bash
npm install
npm run dev
npm run build
npm run preview
```

- Desarrollo: `http://localhost:5173`
- Preview de build: `http://localhost:4173`

## Marca base

Tokens CSS configurados en `src/styles/global.css`:

- Deep Navy: `#083B5C`
- Signal Blue: `#0E7490`
- Trace Teal: `#2DD4BF`
- Ice Background: `#F2FAF8`
- Slate Text: `#0F172A`
- Muted Line: `#B7CDD1`
