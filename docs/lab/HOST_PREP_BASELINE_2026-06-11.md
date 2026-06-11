# Lynjax Host Prep Baseline — 2026-06-11

Purpose: record the current PC readiness for the Lynjax v1.0 virtual/container lab path without modifying the host.

## Probe command

```bash
bash scripts/host-probe.sh
```

## Result summary

- Shell: Git Bash / MSYS on Windows.
- Python: available at `/c/Users/nesal/miniconda3/python`.
- Node: available at `/c/Program Files/nodejs/node`.
- npm: available.
- Git: available.
- curl: available.
- `wsl.exe`: available.
- Docker CLI: missing from current Git Bash/Windows path.
- `VBoxManage`: missing.
- `vagrant`: missing.
- `multipass`: missing.
- `qemu-system-x86_64`: missing.
- `gns3server`: missing.
- `winget.exe`: available, but not used.
- Admin/elevated shell: false.
- Windows: Windows 11 Home Insider Preview Single Language 10.0.26220.
- Computer model: Dell G5 5500.
- RAM: ~15.77 GB.
- Disk C free: ~258.34 GB.
- Disk E free: ~169.48 GB.
- Windows firmware virtualization probe reported `False` in this run. Prior BIOS inspection indicated Intel Virtualization Technology was available, so confirm again inside the selected WSL2/VM path before assuming hardware is blocked.

## Preparation status

Repo-contained artifacts already exist and are safe to use:

- `scripts/host-probe.sh` — read-only host probe.
- `scripts/host_sandbox_probe.sh` — sandbox-oriented host probe.
- `scripts/lab_validate.sh` — fixture/lab validation.
- `scripts/lab_smoke.sh` — lab smoke helper.
- `virtualization/docker-compose.beta.yml` — beta Compose stack for Linux runtime/CI.
- `virtualization/run-beta-compose.sh` — wrapper for Compose commands.
- `virtualization/README.md` — virtualization notes.

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
