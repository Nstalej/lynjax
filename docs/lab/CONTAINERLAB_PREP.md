# Lynjax Containerlab Preparation — v1.0 Test Candidate

Purpose: prepare Lynjax for visual/container-oriented lab inspection without changing the Windows host. This document is a Day 4 preparation artifact for the v1.0 test candidate; it does not require Docker, Containerlab, WSL installation, Hyper-V, or Windows feature changes to read or validate statically.

## Safety boundary

- Windows is the control layer only.
- Runtime execution belongs in WSL2 Ubuntu/Debian, a disposable Ubuntu VM, or GitHub Actions/CI.
- Do not install Docker Desktop, WSL distros, Hyper-V, VirtualBox, Containerlab, GNS3/EVE-NG, drivers, or system packages without Alejandro's explicit approval.
- Do not use real credentials, client data, production IPs, or external scanning targets.
- Keep all demo services localhost-only where ports are published.
- Keep Containerlab topology sanitized: no management credentials, no secrets, no public/customer IP ranges, no real device configs.

## Current PC readiness snapshot

Latest read-only probe command:

```bash
bash scripts/host-probe.sh
```

Observed on 2026-06-14 from Git Bash/MSYS:

- Python: available through Hermes venv path.
- Node/npm: available (`node v24.15.0`, `npm 11.12.1`).
- Git/curl: available.
- `wsl.exe`: available from Windows path, but this run did not confirm a configured Linux distro.
- Docker CLI: missing in Git Bash/Windows path.
- Docker Compose v2: unavailable because Docker CLI is missing.
- VirtualBox/Vagrant/Multipass/QEMU/GNS3: missing from current path.
- `winget.exe`: available, but not used.
- Admin/elevated shell: false.
- RAM: ~15.77 GB.
- Disk free: C ~255 GB, E ~169 GB, G ~3 GB.
- Windows firmware virtualization probe reported `False`; prior BIOS inspection had indicated Intel Virtualization Technology may be available. Re-check inside the selected WSL2/VM route before treating virtualization as blocked.

## VS Code Containerlab extension

Alejandro approved installing/verifying only the VS Code Containerlab extension. Safe verification/install commands:

```bash
# Verify whether the VS Code CLI exists
command -v code

# Verify whether the extension is installed
code --list-extensions | grep -i '^srl-labs\.vscode-containerlab$'

# Approved install if missing and `code` is available
code --install-extension srl-labs.vscode-containerlab

# Re-verify
code --list-extensions | grep -i '^srl-labs\.vscode-containerlab$'
```

Day 4 result: `code` was available. Initial install hit a transient VS Code extension archive error (`invalid stored block lengths`); retry with `--force` succeeded and verification returned `srl-labs.vscode-containerlab`.

Visual usage after opening the repo in VS Code:

1. Open the Lynjax repo folder.
2. Open `virtualization/containerlab/lynjax-demo.clab.yml`.
3. Use the Containerlab extension to inspect the topology visually.
4. Do not deploy from Windows/Git Bash unless Docker/Containerlab are intentionally installed inside a Linux runtime.
5. For Day 5, prefer opening VS Code connected to WSL/Ubuntu or a VM workspace if runtime deployment is approved and prepared.

If `code` is unavailable in a future shell, do not force host changes. Manual step: install/open Visual Studio Code normally, ensure the `code` CLI is on PATH via VS Code's shell command integration, then install extension `srl-labs.vscode-containerlab` from the Extensions panel.

## Route A — WSL2 Ubuntu/Debian runtime

Use when Alejandro approves or confirms an existing WSL2 Linux distro with Docker/Containerlab installed inside Linux.

Expected commands inside WSL, not elevated Windows:

```bash
cd /mnt/c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/host-probe.sh
bash -n scripts/*.sh virtualization/run-beta-compose.sh
bash scripts/lab_validate.sh

# Docker/Compose beta stack
cd virtualization
bash run-beta-compose.sh config
bash run-beta-compose.sh up-detached
bash run-beta-compose.sh ps
bash run-beta-compose.sh logs --tail=80
bash run-beta-compose.sh down
```

Expected localhost checks from Windows/browser after Compose starts:

- Frontend: `http://127.0.0.1:5173/`
- Backend health: `http://127.0.0.1:8000/health`
- Demo target web: `http://127.0.0.1:18080/`
- Demo target metadata: `http://127.0.0.1:18081/metadata.json`

Containerlab static artifact validation/deploy path inside Linux runtime:

```bash
cd /mnt/c/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax
bash scripts/lab_validate.sh
containerlab inspect --topo virtualization/containerlab/lynjax-demo.clab.yml || true

# Deploy only after confirming Docker/Containerlab are intentionally installed in Linux
sudo containerlab deploy --topo virtualization/containerlab/lynjax-demo.clab.yml
sudo containerlab inspect --topo virtualization/containerlab/lynjax-demo.clab.yml
sudo containerlab destroy --topo virtualization/containerlab/lynjax-demo.clab.yml --cleanup
```

## Route B — disposable Ubuntu VM

Use when WSL2 is unsuitable or a cleaner rollback boundary is desired.

1. Create an Ubuntu VM using the chosen hypervisor only after explicit approval.
2. Create a clean snapshot before lab changes.
3. Install Git/Python/Node/Docker/Containerlab inside the VM only.
4. Clone the repo.
5. Run validation and Compose/Containerlab checks.
6. Destroy lab containers and revert snapshot if needed.

Commands inside the VM after prerequisites exist:

```bash
git clone git@github.com:Nstalej/lynjax.git
cd lynjax
bash scripts/host-probe.sh
python -m pytest backend/tests -v
npm --prefix frontend install
npm --prefix frontend run build
bash -n scripts/*.sh virtualization/run-beta-compose.sh
bash scripts/lab_validate.sh
cd virtualization && bash run-beta-compose.sh config
containerlab inspect --topo containerlab/lynjax-demo.clab.yml || true
```

## Route C — CI/GitHub Actions

Use when local Docker/Containerlab are missing. CI can validate static artifacts and, where Docker is available on Ubuntu runners, run Compose checks.

Relevant workflow:

- `.github/workflows/lab-ci.yml`

Expected manual dispatch if path filters skip a docs-only change:

```bash
gh workflow run lab-ci.yml --ref main
RUN_ID=$(gh run list --workflow "Lab CI" --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
```

## Static artifacts in this repo

- `virtualization/docker-compose.beta.yml` — localhost-only beta stack for backend, frontend, demo web target, and metadata target.
- `virtualization/run-beta-compose.sh` — wrapper around Docker Compose v2.
- `virtualization/containerlab/README.md` — artifact-specific notes.
- `virtualization/containerlab/lynjax-demo.clab.yml` — sanitized minimal Containerlab topology for visual inspection and future Linux runtime deployment.

## Cleanup commands

Compose cleanup from Linux runtime:

```bash
cd virtualization
bash run-beta-compose.sh down
```

Containerlab cleanup from Linux runtime after deployment:

```bash
sudo containerlab destroy --topo virtualization/containerlab/lynjax-demo.clab.yml --cleanup
```

Optional Docker cleanup inside disposable Linux runtime only:

```bash
docker ps -a --filter 'name=clab-lynjax-demo' --format '{{.Names}}'
docker network ls --filter 'name=clab'
```

Do not run destructive Docker cleanup against unrelated Docker environments.

## Day 5 v1.0-rc1 validation results

Executed on 2026-06-15:

- Git Bash/Windows:
  - `python -m pytest backend/tests -v`: PASS, 5 tests.
  - `npm --prefix frontend run build`: PASS after rehydrating Rollup optional dependency with `npm install`.
  - `bash -n scripts/*.sh virtualization/run-beta-compose.sh`: PASS.
  - `bash scripts/lab_validate.sh`: PASS; Docker Compose skipped because Docker CLI is missing in Git Bash/Windows PATH.
  - `bash scripts/dev-start.sh && bash scripts/smoke-local.sh && bash scripts/dev-stop.sh`: PASS.
- WSL2 Ubuntu:
  - Docker and Docker Compose are available.
  - `containerlab` is not installed.
  - Python tests and frontend build passed.
  - `bash scripts/lab_validate.sh`: PASS with Docker Compose config validation.
  - `bash virtualization/run-beta-compose.sh up-detached`: PASS.
  - HTTP smoke passed for `127.0.0.1:8000/health`, `127.0.0.1:5173/`, `127.0.0.1:18080/`, and `127.0.0.1:18081/metadata.json`.
  - Stack was stopped with `bash virtualization/run-beta-compose.sh down -v`.

## Limitations for v1.0-rc1

- Current Git Bash/Windows host cannot run Compose/Containerlab because Docker CLI is missing.
- WSL2 Ubuntu can run Docker/Compose, but Containerlab runtime is still missing.
- The Containerlab topology is a sanitized static/demo topology, not a real customer network.
- No external scans or real credentials are part of the v1.0-rc1 test candidate.
- `npm audit --audit-level=high` reports 2 high findings in the Vite/esbuild chain; defer the breaking Vite 8 upgrade to a dedicated branch.
