# Lynjax Next Release Roadmap Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task when active coding starts. Keep Windows as control layer and execute lab/runtime work through WSL2, VM, CI, or repository artifacts; do not require direct Docker-on-Windows installation.

**Goal:** Convert Lynjax beta 0.5 into the next controlled beta/release candidate by reusing only the useful NetVault concepts, completing an end-to-end assessment/report loop, and preparing a more professional virtualized/container lab path.

**Architecture:** Keep Lynjax as the clean product foundation. Treat NetVault as a historical/reference source, not as code to migrate wholesale. Build a narrow, safe field-assessment workflow first: scoped targets, simulated or explicitly authorized checks, local evidence persistence, report generation, and CI-backed lab validation.

**Tech Stack:** FastAPI backend, React/Vite frontend, Markdown/LaTeX/PDF docs, GitHub Actions, Docker Compose inside Linux runtime, later Containerlab topology artifacts.

---

## Calendar and operating agreement

- **2026-06-09:** Alejandro tests beta 0.5; Hermes does not start new build work.
- **2026-06-10:** Alejandro continues beta 0.5 tests; Hermes does not start new build work.
- **2026-06-11 to 2026-06-15:** Five-day next-release sprint.
- **Final-day rule:** keep intermediate work small and verifiable, but produce the final release bundle on Day 5: Markdown docs, LaTeX source, PDF manual, screenshots, status document, release notes, and GitHub release candidate/tag when explicitly ready.
- **Feedback loop:** Alejandro can send test notes from beta 0.5 at any time. Day 1 must triage those notes before coding.

## Version boundary

Recommended next release path:

- **v0.6:** end-to-end minimum: frontend submits to backend, backend returns structured results, frontend renders results, report markdown can be generated from returned data.
- **v0.7:** local evidence/persistence: store executions locally, associate timestamps/evidence, support purge/sanitization.
- **v0.8:** controlled field beta: authorization checklist, scoped safe checks, sanitized technical report.
- **v1.0:** only after the workflow is usable, documented, repeatable in a virtualized lab, and safe enough for controlled demonstrations.

For this five-day sprint, target **v0.6 release candidate** unless Alejandro's beta 0.5 findings are only documentation/packaging fixes. Do not call it v1.0 until the acceptance criteria below are met.

## Current Baseline

Repository: `C:/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax`

Remote: `git@github.com:Nstalej/lynjax.git`

Beta 0.5 contains:

- FastAPI backend with `GET /health`, `GET /api/v1/info`, and `POST /api/v1/assessments/connectivity-demo`.
- React/Vite frontend dashboard using mock data.
- Local scripts: `scripts/dev-start.sh`, `scripts/dev-stop.sh`, `scripts/smoke-local.sh`.
- Lab/virtualization artifacts: `virtualization/docker-compose.beta.yml`, `virtualization/run-beta-compose.sh`, `scripts/host-probe.sh`.
- Docs: user manual, technical manual, local environment guide, virtualized environments guide, LaTeX/PDF manual with screenshots.
- GitHub Actions workflows: backend, frontend, lab.
- GitHub release `v0.5` published with `lynjax-beta-0.5-manual.pdf` asset.

Last known validation from beta 0.5:

```bash
python -m pytest backend/tests -v       # 3 passed
npm --prefix frontend run build         # passed
bash scripts/lab_validate.sh            # passed locally; Docker Compose skipped if unavailable
```

## Open Risks

- Docker/Compose was not available from the current Windows/Git Bash environment; validate Docker Compose in WSL2, VM, or GitHub Actions.
- Current checks are simulated; do not position Lynjax as a production scanner.
- No authentication or credential handling exists; avoid real client credentials.
- No persistence exists yet; reports are template/manual until v0.6 work is implemented.
- NetVault prior code/history must be extracted selectively and sanitized; do not copy old architecture wholesale.
- Host-level installs, admin/elevation, BIOS changes, Windows optional features, Docker Desktop, VirtualBox, VMware, or Hyper-V changes require Alejandro's explicit approval.

---

## Five-day sprint plan

### Day 1 — 2026-06-11: Triage beta 0.5 feedback and lock v0.6 scope

**Objective:** Convert Alejandro's beta 0.5 testing notes plus existing roadmap into an actionable v0.6 scope.

**Files:**
- Create: `docs/plans/2026-06-11-v0.6-sprint-backlog.md`
- Create: `docs/feedback/BETA_0_5_TEST_NOTES.md`
- Modify if needed: `docs/BETA_0_5_STATUS.md`

**Steps:**

1. Pull latest `main` and verify clean state.
2. Run quick baseline checks if dependencies are available:
   - `python -m pytest backend/tests -v`
   - `npm --prefix frontend run build`
   - `bash scripts/lab_validate.sh`
3. Create a beta 0.5 feedback intake document with sections:
   - bugs observed by Alejandro;
   - UX/documentation confusion;
   - environment/setup issues;
   - requested next-release changes;
   - release blockers.
4. Classify items into:
   - must fix for v0.6;
   - defer to v0.7;
   - defer to v1.0;
   - needs Alejandro decision.
5. Decide v0.6 core scope:
   - frontend-to-backend assessment submission;
   - structured result rendering;
   - markdown report generation from response data;
   - improved smoke tests;
   - virtualized lab validation path.
6. Commit docs-only planning changes.

**Verification:** Plan/backlog exists, contains clear acceptance criteria, and current repo status is clean after commit.

### Day 2 — 2026-06-12: Reuse useful NetVault ideas safely

**Objective:** Identify NetVault concepts worth preserving and translate them into Lynjax requirements without importing stale or unsafe implementation wholesale.

**Files:**
- Create: `docs/NETVAULT_REUSE_REVIEW.md`
- Create/modify: `docs/architecture/V0_6_ASSESSMENT_FLOW.md`
- Modify if needed: `backend/app/schemas/assessments.py`
- Modify if needed: `backend/tests/test_api_baseline.py`

**Steps:**

1. Search only targeted local reference paths for NetVault material; do not open large Telegram/session backups unless a specific missing detail requires it.
2. Extract reusable product concepts, for example:
   - network visibility/audit vocabulary;
   - assessment/evidence/report entities;
   - safe target definition ideas;
   - traceability/reporting flow.
3. Explicitly reject unsafe/stale elements:
   - direct production scanning without authorization;
   - unscoped credentials;
   - large unreviewed legacy modules;
   - unclear dependencies.
4. Define v0.6 data contracts for assessment request/response/report payloads.
5. Add or update backend tests for the agreed contract before implementation if code changes are needed.
6. Commit review and contract changes.

**Verification:** `docs/NETVAULT_REUSE_REVIEW.md` explains what is reused, what is rejected, and why; backend tests pass if code/schema changed.

### Day 3 — 2026-06-13: Build end-to-end assessment/report loop

**Objective:** Make the frontend call the backend demo endpoint and generate a report artifact from returned structured data.

**Files:**
- Modify: `backend/app/api/routes/assessments.py`
- Modify: `backend/app/schemas/assessments.py`
- Create/modify: `backend/app/services/reports/`
- Modify: `backend/tests/`
- Modify: `frontend/src/pages/LynjaxDashboard.tsx`
- Create/modify: `frontend/src/lib/api.ts`
- Modify: `reports/templates/assessment-report.md`

**Steps:**

1. Add failing backend tests for stable assessment response fields:
   - assessment ID;
   - target list;
   - check results;
   - evidence summary;
   - timestamp;
   - risk level/status.
2. Implement minimum backend changes to pass tests.
3. Add report generation service that renders markdown from demo results.
4. Expose report output either in the existing endpoint response or a narrow endpoint such as `/api/v1/assessments/connectivity-demo/report`.
5. Add frontend API client with configurable base URL, defaulting to local backend.
6. Replace dashboard mock-only flow with a controlled demo action that calls the backend and renders returned results.
7. Keep all targets sanitized/demo-only.
8. Commit backend and frontend changes separately if meaningful.

**Verification:**

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
bash scripts/dev-start.sh
bash scripts/smoke-local.sh
bash scripts/dev-stop.sh
```

### Day 4 — 2026-06-14: Professional virtualized/container lab preparation

**Objective:** Prepare the next lab path: WSL2/VM first, Compose validation, then Containerlab topology design without requiring host-level installs.

**Files:**
- Modify: `docs/VIRTUALIZED_ENVIRONMENTS.md`
- Create: `docs/lab/CONTAINERLAB_PREP.md`
- Create: `virtualization/containerlab/README.md`
- Create: `virtualization/containerlab/lynjax-demo.clab.yml` if safe/sanitized
- Modify: `.github/workflows/lab-ci.yml` if CI coverage needs expansion
- Modify: `scripts/host-probe.sh` only if read-only checks need improvement

**Steps:**

1. Re-run/read `scripts/host-probe.sh` output if available.
2. Keep the rule: no direct Docker-on-Windows as first path; use WSL2/Ubuntu VM/CI.
3. Validate or document Compose beta behavior in CI/Ubuntu runtime.
4. Add Containerlab preparation docs:
   - required Linux runtime;
   - expected Docker/Containerlab commands;
   - localhost-only/sanitized topology;
   - rollback/cleanup;
   - no real devices/credentials.
5. Add a minimal placeholder topology only if it is safe and CI/lintable; otherwise document exact next steps without pretending it is runnable.
6. Commit lab preparation artifacts.

**Verification:**

```bash
bash -n scripts/host-probe.sh virtualization/run-beta-compose.sh
bash scripts/lab_validate.sh
# If Docker/Compose available in runtime:
cd virtualization && bash run-beta-compose.sh config
```

### Day 5 — 2026-06-15: Final bundle, documentation, screenshots, and release candidate

**Objective:** Generate final deliverables for the sprint and prepare the GitHub release candidate.

**Files:**
- Modify/create: `docs/USER_MANUAL.md`
- Modify/create: `docs/TECHNICAL_MANUAL.md`
- Modify/create: `docs/BETA_0_6_STATUS.md`
- Modify/create: `docs/manual/latex/lynjax-beta-0.6-manual.tex`
- Create: `docs/manual/lynjax-beta-0.6-manual.pdf`
- Create/update: `docs/manual/assets/screenshots/`
- Create: `docs/releases/v0.6-release-notes.md`

**Steps:**

1. Run full local validation available in the environment.
2. Generate virtual screenshots of updated frontend/backend flow.
3. Update Markdown manuals with the v0.6 workflow.
4. Generate LaTeX manual and compile PDF.
5. Write v0.6 status and release notes.
6. Check git diff for secrets, generated junk, stale local logs, and accidental node/cache files.
7. Commit final docs/artifacts.
8. Push branch/main according to repository policy.
9. If Alejandro has approved release publication, create GitHub release/tag `v0.6` or `v0.6-rc1` and attach PDF. If not approved, prepare release notes and report that it is ready for approval.

**Verification:**

```bash
python -m pytest backend/tests -v
npm --prefix frontend run build
bash scripts/lab_validate.sh
# If services can run:
bash scripts/dev-start.sh
bash scripts/smoke-local.sh
bash scripts/dev-stop.sh
```

---

## Acceptance criteria for v0.6

- Frontend can initiate at least one safe demo assessment through the backend.
- Backend returns structured results with traceable evidence fields.
- A markdown report can be generated from actual returned data, not only static template text.
- Documentation explains setup, operation, limits, and cleanup.
- Virtualization path is clear: WSL2/VM/CI first, Compose beta validated where Docker exists, Containerlab preparation documented.
- Tests/builds pass in available environment.
- Final artifacts exist in repo: Markdown, LaTeX, PDF, screenshots, release notes.
- GitHub release is created only after final validation and approval if the version is more than a release candidate.

## Not in scope for v0.6

- Real SNMP discovery.
- Credential vault or secrets management.
- Production-grade authentication.
- Real client network scanning.
- GNS3/EVE-NG implementation.
- Full NetVault code migration.

## Suggested release naming

- Use `v0.6-rc1` if Day 5 delivers the flow but Alejandro still needs to test.
- Use `v0.6` if Alejandro's beta feedback is incorporated and validation is clean.
- Reserve `v1.0` for the first controlled field-beta-ready release with authorization workflow, evidence purge, virtualized lab repeatability, and complete user/technical manuals.
