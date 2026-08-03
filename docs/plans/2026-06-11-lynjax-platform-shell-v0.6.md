# Lynjax Platform Shell v0.6 — 5-Day Deep Sprint Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task when coding starts. Keep Lynjax as the clean product foundation. Use NetVault only as historical reference for concepts; do not migrate old code wholesale.

**Created:** 2026-06-10 18:58 HAC  
**Target start:** 2026-06-11  
**Goal:** Build the Lynjax Platform Shell: a modern, animated, bilingual, modular frontend foundation for v0.6 that can later connect to backend assessment, device, AD, reports and LLM/MCP features.

**Architecture:** Frontend-first shell using React/Vite, route-based modules, shared layout components, i18n keys for all user-facing strings, mock/demo data behind typed interfaces, and future API integration points. Backend changes are limited to contract awareness unless needed for smoke validation.

**Tech Stack:** React/Vite, TypeScript, CSS/Tailwind-style token system or current CSS architecture, lucide-react icons, react-i18next/i18next, optional Framer Motion only if dependency cost is acceptable, FastAPI backend kept as current v0.5 baseline.

---

## Current Baseline

Repository: `C:/Users/nesal/Documents/001_Programas/lynjax`

Current Lynjax beta 0.5 contains:

- FastAPI backend with:
  - `GET /health`
  - `GET /api/v1/info`
  - `POST /api/v1/assessments/connectivity-demo`
- React/Vite frontend with a single-page visual dashboard in `frontend/src/pages/LynjaxDashboard.tsx`.
- Brand tokens and mock assessment data in `frontend/src/lib/brand.ts`.
- Existing manuals, LaTeX/PDF manual and screenshots.
- Existing roadmap: `docs/plans/2026-06-11-lynjax-next-release-roadmap.md`.
- NetVault review now available: `docs/NETVAULT_LEGACY_REVIEW_2026-06-11.md`.

## Product Decision

For v0.6, prioritize **Lynjax Platform Shell** over legacy feature migration.

NetVault is now treated as:

- A reference for module names and long-term product direction.
- A source of historical requirements: devices, connectivity, AD, MCP/LLM, reports, topology.
- Not a source to copy directly into Lynjax.

## v0.6 Platform Shell Scope

### In scope

- Modern app shell.
- Animated collapsible sidebar.
- Responsive mobile drawer behavior.
- Topbar with language switcher.
- ES/EN i18n from the start.
- Route structure for future modules.
- Mock data displayed through typed interfaces.
- Visual placeholders for unimplemented modules.
- Accessibility guardrails:
  - skip link;
  - keyboard focus states;
  - no `transition: all`;
  - `prefers-reduced-motion` support;
  - semantic buttons/links;
  - no unwanted horizontal overflow.
- Build/test verification.

### Not in scope for this first shell pass

- Full NetVault migration.
- Production auth/RBAC.
- Credential vault.
- Real SNMP.
- Real Active Directory agent integration.
- Real LLM/MCP execution.
- Network actions/HITL.
- Real client scanning.

## Target Navigation

The shell should include these modules, even if some are placeholders:

1. Overview
2. Assets
3. Connectivity
4. Assessments
5. Evidence
6. Reports
7. Topology
8. Directory / Active Directory
9. Intelligence / LLM
10. Settings

## Desired Visual Behavior

- Sidebar expanded by default on desktop.
- Sidebar collapsible to icon-only mode.
- Smooth width/opacity transitions.
- Mobile sidebar opens as drawer from left.
- Active route highlighted with Lynjax teal/blue accent.
- Topbar contains:
  - current page title;
  - environment/status indicator;
  - language switcher;
  - future user/settings area.
- Main content uses cards, panels, badges and empty states.
- Existing Lynjax palette must remain:
  - Deep Navy `#083B5C`
  - Signal Blue `#0E7490`
  - Trace Teal `#2DD4BF`
  - Ice Background `#F2FAF8`
  - Slate Text `#0F172A`
  - Muted Line `#B7CDD1`

---

# 5-Day Sprint

## Day 1 — Platform Shell foundation

**Objective:** Replace the single-page dashboard with a real app shell and route structure.

**Files:**

- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/layout/AppShell.tsx`
- Create: `frontend/src/layout/Sidebar.tsx`
- Create: `frontend/src/layout/Topbar.tsx`
- Create: `frontend/src/layout/MobileDrawer.tsx` if useful
- Create: `frontend/src/components/nav/navItems.ts`
- Create/modify: `frontend/src/styles/global.css`
- Create: `frontend/src/pages/OverviewPage.tsx`
- Create placeholder pages for all target modules

**Steps:**

1. Inspect current frontend dependency list in `frontend/package.json`.
2. Decide whether current dependencies are enough or whether to add router/i18n/motion libraries.
3. Add route structure for all target modules.
4. Build `AppShell` with sidebar + topbar + main outlet/content.
5. Implement sidebar expanded/collapsed desktop behavior.
6. Implement mobile drawer behavior or prepare responsive fallback.
7. Add placeholder pages with clear product language.
8. Preserve accessibility skip link.
9. Run frontend build.

**Verification:**

```bash
npm --prefix frontend run build
```

Expected: build passes.

## Day 2 — i18n ES/EN and content system

**Objective:** Add bilingual foundation and remove hardcoded user-facing strings from shell components.

**Files:**

- Create: `frontend/src/i18n/index.ts`
- Create: `frontend/src/i18n/locales/en/common.json`
- Create: `frontend/src/i18n/locales/es/common.json`
- Create: `frontend/src/components/LanguageSwitcher.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: shell/pages created on Day 1

**Steps:**

1. Install/configure i18n dependencies if missing.
2. Configure fallback language: English.
3. Enable browser/localStorage language persistence.
4. Add switcher in topbar.
5. Move nav labels, page titles, empty states and actions into locale files.
6. Verify Spanish and English labels visually/build-wise.

**Verification:**

```bash
npm --prefix frontend run build
```

Expected: build passes and no obvious untranslated hardcoded shell strings remain.

## Day 3 — Module visuals and reusable UI components

**Objective:** Make the shell feel like a real Lynjax platform, not a generic admin template.

**Files:**

- Create: `frontend/src/components/ui/StatusCard.tsx`
- Create: `frontend/src/components/ui/StatusBadge.tsx`
- Create: `frontend/src/components/ui/EmptyState.tsx`
- Create: `frontend/src/components/ui/ModulePanel.tsx`
- Create: `frontend/src/components/ui/DataTable.tsx` if useful
- Modify: module pages
- Modify: `frontend/src/lib/brand.ts` or create `frontend/src/lib/mockData.ts`

**Steps:**

1. Create reusable card/panel/badge components.
2. Build Overview with status cards:
   - visible assets;
   - active checks;
   - evidence items;
   - report readiness;
   - risk highlights.
3. Build Assets page mock table.
4. Build Connectivity page mock checks.
5. Build Assessments/Evidence/Reports pages with actionable placeholders.
6. Build Directory/AD page as planned module, not active integration.
7. Build Intelligence/LLM page as planned module, not active integration.
8. Keep copy bilingual.

**Verification:**

```bash
npm --prefix frontend run build
```

Expected: build passes.

## Day 4 — API-ready contracts and backend connection preparation

**Objective:** Prepare the frontend to connect to the current backend endpoint without forcing the whole platform to be real yet.

**Files:**

- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/types/platform.ts`
- Modify: `frontend/src/pages/ConnectivityPage.tsx` or `AssessmentsPage.tsx`
- Optionally modify: `backend/app/schemas/assessments.py` only if contract is unclear
- Optionally create: `docs/architecture/V0_6_PLATFORM_SHELL_CONTRACTS.md`

**Steps:**

1. Define frontend types:
   - `Asset`;
   - `ConnectivityCheck`;
   - `AssessmentResult`;
   - `EvidenceItem`;
   - `ReportArtifact`;
   - `DirectorySnapshot`;
   - `AgentStatus`;
   - `IntelligenceModuleStatus`.
2. Add API client with base URL env support.
3. Keep mock data behind the same types used by future API responses.
4. Optionally wire one safe action to `/api/v1/assessments/connectivity-demo` if time allows.
5. Document expected contracts.

**Verification:**

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
```

Expected: backend tests pass and frontend build passes.

## Day 5 — Self-audit, screenshots, docs, and v0.6 RC readiness

**Objective:** Finish the shell as a clean v0.6 release-candidate foundation.

**Files:**

- Modify: `docs/BETA_0_5_STATUS.md` or create `docs/BETA_0_6_PLATFORM_SHELL_STATUS.md`
- Modify: `docs/USER_MANUAL.md`
- Modify: `docs/TECHNICAL_MANUAL.md`
- Create: `docs/releases/v0.6-platform-shell-release-notes.md`
- Update screenshots under `docs/manual/assets/screenshots/` if services can run
- Update LaTeX/PDF manual if this is selected as the deliverable for the sprint

**Steps:**

1. Run validation.
2. Self-audit visual code against web interface guidelines:
   - accessibility;
   - focus states;
   - reduced motion;
   - overflow;
   - semantic controls;
   - i18n completeness.
3. Fix obvious violations.
4. Update docs with the platform shell modules and known limits.
5. Capture screenshots if frontend can run.
6. Prepare release notes.
7. Do not publish final release without Alejandro approval.

**Verification:**

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
bash scripts/lab_validate.sh
```

Expected: available checks pass; unavailable runtime limits are documented.

---

## Acceptance Criteria

The v0.6 Platform Shell is acceptable when:

- The app has a modern shell with sidebar, topbar and routed modules.
- Sidebar supports animated expanded/collapsed states on desktop.
- The UI is bilingual ES/EN.
- All core planned modules appear in navigation.
- Directory/AD and Intelligence/LLM are clearly marked as planned/future, not falsely active.
- Mock data is typed and structured for later API integration.
- Frontend build passes.
- Backend tests still pass.
- Documentation explains that this is a platform shell and not yet production scanning.

## Open Risks

- Adding too many libraries may slow the sprint; prefer simple CSS transitions unless Framer Motion is clearly worth it.
- The current frontend may not yet have routing/i18n dependencies.
- Backend is still v0.5 demo-level; avoid making the shell imply production capability.
- NetVault legacy modules must not be copied directly without contract review and tests.

## First command sequence for Day 1

```bash
cd /c/Users/nesal/Documents/001_Programas/lynjax
git status --short --branch
python -m pytest backend/tests -v
npm --prefix frontend run build
```

Then inspect:

```bash
cat frontend/package.json
find frontend/src -maxdepth 3 -type f | sort
```

Use Hermes file/search tools instead of shell `cat/find` when working inside this environment.
