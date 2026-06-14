# Lynjax Host Prep Baseline — 2026-06-11

Purpose: record the current PC readiness for the Lynjax v1.0 virtual/container lab path without modifying the host.

## Probe command

```bash
bash scripts/host-probe.sh
```

## Result summary

Latest read-only probe refresh on 2026-06-14:

- Shell: Git Bash / MSYS on Windows.
- Python: available at `/c/Users/nesal/AppData/Local/hermes/hermes-agent/venv/Scripts/python`.
- Node: available at `/c/Program Files/nodejs/node` (`v24.15.0`).
- npm: available (`11.12.1`).
- Git: available.
- curl: available.
- `wsl.exe`: available from Windows path; the probe did not confirm a configured Linux distro.
- Docker CLI: missing from current Git Bash/Windows path.
- Docker Compose v2: unavailable because Docker CLI is missing.
- `VBoxManage`: missing.
- `vagrant`: missing.
- `multipass`: missing.
- `qemu-system-x86_64`: missing.
- `gns3server`: missing.
- `winget.exe`: available, but not used.
- VS Code CLI `code`: available.
- VS Code Containerlab extension: installed/verified as `srl-labs.vscode-containerlab` on 2026-06-14 after one transient extension archive retry.
- Admin/elevated shell: false.
- Windows: Windows 11 Home Insider Preview Single Language 10.0.26220.
- Computer model: Dell G5 5500.
- RAM: ~15.77 GB.
- Disk C free: ~255.27 GB.
- Disk E free: ~169.48 GB.
- Disk G free: ~3.09 GB.
- Windows firmware virtualization probe reported `False` in this run. Prior BIOS inspection indicated Intel Virtualization Technology was available, so confirm again inside the selected WSL2/VM path before assuming hardware is blocked.

Historical 2026-06-11 baseline retained the same broad blocker: Docker/Compose and heavy virtual lab tools were not available in the current Git Bash host.

## Preparation status

Repo-contained artifacts already exist and are safe to use:

- `scripts/host-probe.sh` — read-only host probe.
- `scripts/host_sandbox_probe.sh` — sandbox-oriented host probe.
- `scripts/lab_validate.sh` — fixture/lab/static Containerlab validation.
- `scripts/lab_smoke.sh` — lab smoke helper.
- `virtualization/docker-compose.beta.yml` — beta Compose stack for Linux runtime/CI.
- `virtualization/run-beta-compose.sh` — wrapper for Compose commands.
- `virtualization/README.md` — virtualization notes.
- `docs/lab/CONTAINERLAB_PREP.md` — Day 4 Containerlab/WSL2/VM/CI preparation guide.
- `virtualization/containerlab/README.md` — sanitized Containerlab artifact notes.
- `virtualization/containerlab/lynjax-demo.clab.yml` — minimal static Containerlab topology for visual inspection/future Linux runtime deployment.

## Current blocker for local container execution

Docker/Compose is not available in the current Git Bash host. Therefore:

- Do not run Containerlab or Compose directly on Windows/Git Bash.
- Use WSL2 Ubuntu/Debian, an Ubuntu VM, or CI for Compose/Containerlab execution.
- Do not install Docker Desktop or enable Windows features without Alejandro's explicit approval.

## Next safe preparation steps

1. Keep Windows as the control workstation.
2. Use repo scripts/docs to validate static lab files from Git Bash.
3. On Day 4, add/validate Containerlab preparation artifacts under `virtualization/containerlab/`.
4. On Day 5, run base tests locally where possible and document any Docker/Containerlab runtime steps that require WSL2/VM execution.
