# External Lynjax Workspace Migration — 2026-07-06

## Canonical repository

`C:/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax`

Remote: `git@github.com:Nstalej/lynjax.git`

## Source evaluated

`C:/Users/nesal/Documents/001_Programas/lynjax`

That external folder was not a Git repository and represented an older Beta 0.5 brand/foundation workspace. Backend/frontend/lab implementation in the canonical repo is newer.

## Migrated as finalized/stable Lynjax assets

- `DESIGN.md` → canonical root `DESIGN.md`
- `docs/branding/brand-brief.md` → `docs/branding/brand-brief.md`
- `assets/logo/lynjax-logo-concept.svg` → `brand/assets/source/logo/lynjax-logo-concept.svg`
- `assets/logo/lynjax-icon-concept.svg` → `brand/assets/source/logo/lynjax-icon-concept.svg`
- `docs/plans/2026-05-30-lynjax-beta-0.5-foundation.md` → `docs/plans/2026-05-30-lynjax-beta-0.5-foundation.md` with canonical-path migration notes

## Archived, not promoted

- External `README.md` was archived as `README.external-original.md` because it describes a future skeleton and conflicts with the newer v1.0-rc1 canonical README.
- Empty `.gitkeep` placeholders from the external backend/frontend/labs/data/reports/scripts folders were not migrated because the canonical repo already has real implementations.

## Hardening/ECC note

Tools and agents should use the canonical repo root, not the obsolete external folder:

```bash
cd /c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
```

The obsolete external folder was moved to `C:/Users/nesal/Documents/001_Programas/_archived_workspaces/lynjax-external-migrated-20260706`, leaving no active top-level `lynjax` workspace for scanners to confuse with the canonical frontend/project.
