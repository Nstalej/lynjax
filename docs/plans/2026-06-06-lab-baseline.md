# Lynjax Local Lab Baseline Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Prepare a safe, reproducible local Docker lab foundation so Lynjax can run demo assessments after Day 5.

**Architecture:** The lab starts with isolated Docker Compose targets and static fixtures. Scripts wrap validation/up/down operations without touching real networks. CI validates lab structure and compose syntax so future backend/reporting work has stable fixtures.

**Tech Stack:** Docker Compose, Bash, Python stdlib JSON validation, GitHub Actions.

---

## Current Baseline

- Repo: `Nstalej/lynjax`, public, `main` clean before this branch.
- Current backend/frontend are still structural placeholders.
- Local Docker is not available in the current Windows Hermes shell, so local validation must skip runtime compose operations when Docker is missing.
- GitHub Actions runners can validate compose syntax with Docker/Compose available.

## Task 1: Add safe lab fixtures

**Objective:** Define a small, non-sensitive lab scope that future backend/reporting code can consume.

**Files:**
- Create: `lab/sample-data/targets.json`
- Create: `lab/sample-data/assessment-scope.json`
- Create: `lab/sample-data/expected-checks.json`

**Verification:** Run `bash scripts/lab_validate.sh` and confirm JSON fixtures parse.

## Task 2: Add Docker Compose lab

**Objective:** Provide deterministic local targets for HTTP checks without external scans.

**Files:**
- Create: `lab/docker/docker-compose.yml`
- Create: `lab/docker/target-web/index.html`
- Create: `lab/docker/target-web/nginx.conf`
- Create: `lab/docker/target-metadata/metadata.json`

**Verification:** If Docker Compose is available, run `docker compose -f lab/docker/docker-compose.yml config`.

## Task 3: Add operator scripts

**Objective:** Make lab validation/start/stop repeatable.

**Files:**
- Create: `scripts/lab_validate.sh`
- Create: `scripts/lab_up.sh`
- Create: `scripts/lab_down.sh`
- Create: `scripts/lab_smoke.sh`

**Verification:** Run `bash scripts/lab_validate.sh`. On machines without Docker, the script should validate files and skip compose validation cleanly.

## Task 4: Document lab workflow

**Objective:** Explain what the lab is, what it is not, and how to run it safely.

**Files:**
- Create: `lab/README.md`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/ROADMAP_5_DAYS.md`

**Verification:** Read docs and confirm they align with the Day 5 goal: local lab first, no real networks by default.

## Task 5: Add Lab CI

**Objective:** Validate lab assets and compose syntax on every PR touching lab/scripts/workflow files.

**Files:**
- Create: `.github/workflows/lab-ci.yml`

**Verification:** GitHub Actions should pass `Lab CI` on the PR, including a Docker Compose startup and HTTP probe smoke test.

## Open Risks

- Docker is not installed/available in the current Hermes shell, so actual `docker compose up` must be tested later on a Docker-capable machine.
- This lab only provides safe HTTP/static targets; SSH/SNMP and richer network scenarios remain future work.
