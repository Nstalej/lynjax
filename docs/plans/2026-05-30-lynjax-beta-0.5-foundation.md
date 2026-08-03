> **Migration note:** This is the original Beta 0.5 foundation plan migrated from the obsolete external `C:/Users/nesal/Documents/001_Programas/lynjax` workspace. Use `C:/Users/nesal/Documents/001_Programas/lynjax` as the canonical repository. Some baseline/open-risk statements are historical and are superseded by the v1.0-rc1 docs.

# Lynjax Beta 0.5 Foundation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build Lynjax as a clean beta 0.5 foundation for authorized network assessment, traceable evidence and technical reporting.

**Architecture:** Lynjax starts as a new local-first workspace instead of copying NetVault wholesale. The beta uses a FastAPI backend, a lightweight React/Vite dashboard, SQLite for local assessment data, JWT/RBAC from day one, and Docker Compose only for demo/lab targets. NetVault remains a reference repository; only verified code and concepts are migrated.

**Tech Stack:** Python 3.11, FastAPI, SQLite/SQLModel or SQLAlchemy, pytest, React/Vite, Tailwind, Docker Compose, bash smoke scripts, Markdown report generation.

---

## Current Baseline — 2026-05-30

**Historical workspace:** `C:/Users/nesal/Documents/001_Programas/lynjax` (migrated)
**Canonical workspace:** `C:/Users/nesal/Documents/001_Programas/lynjax`

**Decisions made:**

- Product name: **Lynjax**.
- Primary tagline: **Intelligent Network Visibility**.
- Extended line: **Intelligent network audit, assessment and traceability for real infrastructure.**
- Old NetVault repo remains historical reference.
- New work should not copy tests/code that ignore JWT/RBAC.
- First lab path is local venv + optional Docker Compose, not GNS3/EVE-NG.

**Created now:**

- `README.md`
- `DESIGN.md`
- `docs/branding/brand-brief.md`
- `assets/logo/lynjax-logo-concept.svg`
- `assets/logo/lynjax-icon-concept.svg`

## Open Risks

- Domain availability should still be confirmed and purchased through the registrar.
- Trademark/name collision has not been legally cleared.
- The logo is a first editable SVG concept, not final brand artwork.
- Backend/frontend are not implemented yet.
- NetVault migration candidates still need code-level review.

---

## Definition of Done — Beta 0.5 Foundation

Lynjax beta 0.5 foundation is ready when:

1. The repo has a documented local dev environment.
2. Backend health endpoint works.
3. JWT login works from day one.
4. Protected routes have tests that send valid auth headers.
5. A local assessment can be created with authorized scope.
6. Devices can be registered manually.
7. Basic checks can be executed against demo/local targets.
8. A Markdown assessment report can be generated.
9. Frontend shell shows login, dashboard, assessment and report pages.
10. A smoke script validates backend, tests and frontend build.

---

## Track A — Brand and repo foundation

### Task A1: Initialize git repository

**Objective:** Track Lynjax cleanly from the first commit.

**Files:**
- Existing: all current files.
- Create: `.gitignore`

**Steps:**

1. Create `.gitignore` for Python, Node, data and reports.
2. Run `git init`.
3. Run `git status`.
4. Commit brand foundation.

**Commands:**

```bash
cd C:/Users/nesal/Documents/001_Programas/lynjax
git status --short --branch
git add DESIGN.md docs/branding/brand-brief.md brand/assets/source/logo docs/plans/2026-05-30-lynjax-beta-0.5-foundation.md
git commit -m "docs: migrate lynjax brand foundation into canonical repo"
```

### Task A2: Validate DESIGN.md

**Objective:** Ensure the brand token spec is machine-readable and contrast-aware.

**Files:**
- Existing: `DESIGN.md`
- Optional create: `assets/brand/tailwind.theme.json`

**Commands:**

```bash
npx -y @google/design.md lint DESIGN.md
npx -y @google/design.md export --format tailwind DESIGN.md > assets/brand/tailwind.theme.json
```

**Expected:** no structural errors; review any WCAG warnings.

---

## Track B — Backend foundation

### Task B1: Create Python project skeleton

**Objective:** Create minimal backend layout without migrating NetVault code yet.

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/tests/test_health.py`

**Implementation target:** FastAPI app with `/health` returning product/version/status.

**Verification:**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
pytest -q
```

### Task B2: Add JWT auth from day one

**Objective:** Prevent recurrence of NetVault tests failing because auth was bolted on later.

**Files:**
- Create: `backend/app/auth/security.py`
- Create: `backend/app/auth/routes.py`
- Create: `backend/tests/test_auth.py`

**Acceptance:**

- Login returns JWT.
- Protected test route rejects missing token.
- Protected test route accepts valid token.

---

## Track C — Assessment model

### Task C1: Define assessment scope model

**Objective:** Store authorized assessment scope before any checks run.

**Files:**
- Create: `backend/app/assessments/models.py`
- Create: `backend/app/assessments/routes.py`
- Create: `backend/tests/test_assessments.py`

**Fields:**

- assessment ID;
- client/project name;
- authorized CIDR/ranges;
- operator notes;
- created timestamp;
- retention/purge flag.

### Task C2: Define device model

**Objective:** Allow manual device registration.

**Files:**
- Create: `backend/app/devices/models.py`
- Create: `backend/app/devices/routes.py`
- Create: `backend/tests/test_devices.py`

**Fields:**

- hostname/label;
- IP;
- device type;
- assessment ID;
- tags;
- notes.

---

## Track D — Reports and evidence

### Task D1: Create Markdown report generator

**Objective:** Generate useful deliverable before building complex monitoring.

**Files:**
- Create: `backend/app/reports/assessment_report.py`
- Create: `backend/templates/reports/assessment_es.md.j2`
- Create: `backend/templates/reports/assessment_en.md.j2`
- Create: `backend/tests/test_assessment_report.py`

**Sections:**

```text
Executive summary
Authorized scope
Devices reviewed
Evidence
Findings
Risks
Recommendations
Next steps
```

---

## Track E — Frontend and landing shell

### Task E1: Create product landing shell

**Objective:** Present Lynjax professionally while backend foundation is built.

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Use: `DESIGN.md` tokens manually or exported Tailwind theme.

**Sections:**

- Hero with Lynjax logo.
- Value proposition.
- Assessment workflow.
- Report/evidence focus.
- Local-first beta note.

### Task E2: Create dashboard shell

**Objective:** Create visual structure for future app routes.

**Pages:**

- Login.
- Assessments.
- Devices.
- Evidence.
- Reports.

---

## Track F — Local demo/lab

### Task F1: Create Docker Compose local demo

**Objective:** Test checks without physical switches.

**Files:**
- Create: `labs/local-demo/docker-compose.yml`
- Create: `labs/local-demo/README.md`

**Targets:**

- HTTP demo service.
- TCP open-port target.
- Future SNMP simulator.

---

## Track G — Smoke verification

### Task G1: Add smoke script

**Objective:** One command verifies the beta foundation.

**Files:**
- Create: `scripts/smoke_check.sh`

**Checks:**

- backend compile/test;
- frontend build;
- report generator test;
- optional local demo config validation.

**Command:**

```bash
bash scripts/smoke_check.sh
```
