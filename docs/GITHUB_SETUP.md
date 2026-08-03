# GitHub setup para Lynjax

Este documento conecta la estructura local de Lynjax con GitHub sin crear el remoto automáticamente desde tareas programadas.

## Estado esperado local

Ruta local:

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
```

Si todavía no es repositorio Git local:

```bash
git init -b main
git status --short
```

Si Git no soporta `git init -b main`, usa:

```bash
git init
git branch -M main
git status --short
```

## Validar si ya existe remoto

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
git remote -v
```

Si aparece `origin`, valida acceso sin cambiar nada:

```bash
git ls-remote --heads origin
```

## Crear repo remoto con GitHub CLI

> Requiere confirmación humana antes de ejecutarlo. No lo ejecutes desde una tarea programada sin aprobación.

Validar autenticación:

```bash
gh auth status
```

Crear un repositorio privado recomendado para el rebrand:

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
gh repo create Nstalej/lynjax --private --source=. --remote=origin --description "Lynjax rebrand lab: FastAPI + Vite baseline"
```

Alternativa pública si Alejandro decide publicarlo:

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
gh repo create Nstalej/lynjax --public --source=. --remote=origin --description "Lynjax rebrand lab: FastAPI + Vite baseline"
```

## Conectar un remoto existente

Si el repo ya fue creado en GitHub, conecta `origin` así:

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
git remote add origin git@github.com:Nstalej/lynjax.git
git remote -v
git ls-remote --heads origin
```

Si `origin` existe pero apunta a otra URL:

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
git remote set-url origin git@github.com:Nstalej/lynjax.git
git remote -v
git ls-remote --heads origin
```

## Primer commit y push

Después de confirmar el remoto correcto:

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
git add README.md .gitignore .github/workflows/backend-ci.yml .github/workflows/frontend-ci.yml docs/GITHUB_SETUP.md backend frontend docs brand reports lab scripts
git commit -m "chore: add Lynjax GitHub CI baseline"
git push -u origin main
```

## CI incluido

- `.github/workflows/backend-ci.yml`: baseline Python/FastAPI. Instala dependencias si existen, ejecuta `ruff`, `compileall` y `pytest` sólo cuando haya archivos Python/tests.
- `.github/workflows/frontend-ci.yml`: baseline Node/Vite. Instala dependencias y ejecuta `lint`, `test` y `build` sólo cuando exista `frontend/package.json` y los scripts estén definidos.
