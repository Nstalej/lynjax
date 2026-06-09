# Lynjax Local Virtualization Lab Host Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task after Alejandro approves any host-level installation.

**Goal:** Prepare Alejandro's Windows laptop as a safe, local, virtualized lab host for Lynjax without installing Docker directly on the Windows base system or affecting the host more than necessary.

**Architecture:** Keep Windows as the control/workstation layer only. Run container/network lab tooling inside an isolated Linux sandbox first, then graduate to a dedicated Linux VM for Containerlab/GNS3/EVE-NG style labs. Preserve a simple Docker Compose beta lab as the first reproducible scenario.

**Tech Stack:** Windows 11 Home, Git Bash, GitHub Actions, optional WSL2 Ubuntu sandbox, optional Ubuntu VM, Docker/Podman inside Linux only, future Containerlab, future GNS3/EVE-NG.

---

## Current Baseline — 2026-06-06/07

**Repository:** `C:\Users\nesal\Documents\001_Programas\netvault-rebrand-lab\lynjax`

**GitHub:** `https://github.com/Nstalej/lynjax`

**Merged PRs:**

- PR #1: backend CI cache fix.
- PR #2: local Docker Compose lab baseline.

**Latest verified main CI:**

- `Lab CI` on `main`: success after PR #2 merge.
- Historical first-push Backend CI failure exists but was already fixed by PR #1.

**Host inspection results:**

- OS: Windows 11 Home Insider Preview Single Language, build `26220`, 64-bit.
- Machine: Dell G5 5500.
- CPU: Intel Core i7-10750H, 6 cores / 12 threads.
- RAM: ~16 GB total; ~7.7 GB free during inspection.
- Disk free:
  - `C:` ~280 GB free.
  - `E:` ~181 GB free.
  - `G:` ~3.3 GB free.
- Current user is not elevated/admin during this Hermes session.
- `winget.exe` is available.
- `wsl.exe` exists, but WSL is not installed/configured.
- Docker is not installed/available locally.
- `VBoxManage`, `vagrant`, `multipass`, `qemu-system-x86_64`, and `gns3server` are not currently available.
- Windows optional feature inspection requires elevation and could not be completed from the current non-admin session.
- PowerShell CIM reported `HypervisorPresent=true`, but also reported virtualization firmware flags as false. This needs a manual BIOS/Windows verification before relying on WSL2, VirtualBox, or nested labs.

**Recovered product/lab context:**

- First lab path: simple local lab with Docker Compose and safe fixtures.
- Next path: evaluate Containerlab after the local beta workflow is stable.
- GNS3/EVE-NG are useful later for visual or enterprise-style labs but should not block beta 0.2/0.5.
- No physical switches are required for the initial beta lab.

---

## Guiding Rules

1. **Do not install Docker directly on Windows as the first step.** Keep container engines inside Linux sandbox/VM layers.
2. **Do not install host-level packages without explicit approval.** Anything using `winget`, Windows optional features, BIOS changes, or admin elevation needs Alejandro's confirmation.
3. **Prefer reversible layers:** WSL distribution export/import, VM snapshots, repo scripts, and documented commands.
4. **Keep labs localhost-only by default.** Expose services only to `127.0.0.1` unless a later test requires otherwise.
5. **No real client data in the public repo.** Use sanitized fixtures only.
6. **Local beta first, heavy simulators later.** Containerlab/GNS3/EVE-NG come after the local Docker Compose lab is stable.

---

## Target Lab Evolution

### Lab 0 — CI-backed local fixtures, already started

Purpose: prove the repository can validate lab definitions without relying on Alejandro's host.

Current files:

- `lab/docker/docker-compose.yml`
- `lab/sample-data/*.json`
- `scripts/lab_validate.sh`
- `scripts/lab_up.sh`
- `scripts/lab_smoke.sh`
- `scripts/lab_down.sh`
- `.github/workflows/lab-ci.yml`

Status: merged via PR #2 and green on GitHub Actions.

### Lab 1 — Local sandbox beta lab

Purpose: allow Alejandro/Hermes to run the same Docker Compose lab locally, but inside an isolated Linux environment.

Preferred implementation after approval:

- Enable/install WSL2 Ubuntu or Debian.
- Install container runtime inside WSL only.
- Clone/use Lynjax repo inside WSL or mount the repo carefully.
- Run:
  - `bash scripts/lab_validate.sh`
  - `bash scripts/lab_up.sh`
  - `bash scripts/lab_smoke.sh`
  - `bash scripts/lab_down.sh`

Acceptance criteria:

- Windows host does not run Docker Desktop as the main container engine.
- Lab endpoints remain local.
- The lab can be torn down completely.

### Lab 2 — Dedicated Linux VM lab host

Purpose: isolate heavier networking tooling away from Windows and WSL.

Preferred implementation after Lab 1:

- Install a type-2/open virtualization tool only after confirming BIOS virtualization support.
- Create an Ubuntu LTS VM with a snapshot named `clean-lab-base`.
- Install Docker/Podman and lab tools inside the VM only.
- Use shared folder or git clone for Lynjax.
- Run Compose lab and future Containerlab inside the VM.

Why this matters:

- Easier snapshots/rollback.
- Cleaner separation from Windows.
- Better place for Containerlab than the host OS.

### Lab 3 — Containerlab automation

Purpose: create reproducible network topologies from YAML.

Candidate scenarios:

- Lightweight Linux containers responding to TCP/HTTP/SSH checks.
- FRRouting/containerized routers if the laptop can handle them.
- SNMP simulator later.
- Lynjax backend evaluates these targets and produces reports.

Acceptance criteria:

- Topology files are versioned.
- No proprietary images are required for the first topology.
- Lab teardown is automatic.

### Lab 4 — GNS3/EVE-NG evaluation

Purpose: visual/enterprise-style labs after Lynjax beta is stable.

Order:

1. GNS3 if a visual desktop topology is needed.
2. EVE-NG only if the VM resources and nested virtualization are acceptable.

Do not start here. These tools can consume time and machine resources before Lynjax has its basic assessment/report flow stable.

---

## Implementation Tasks

### Task 1: Confirm virtualization prerequisites manually

**Objective:** Decide whether WSL2/VM layers are safe on this laptop.

**Files:**

- Modify: this plan only if results differ.

**Steps:**

1. Open BIOS/UEFI and check Intel VT-x / Virtualization Technology.
2. In Windows, open an elevated terminal and verify optional features if approved:
   - `VirtualMachinePlatform`
   - `Microsoft-Windows-Subsystem-Linux`
   - `Windows-Hypervisor-Platform`
3. Do not enable anything until Alejandro approves the chosen route.

**Expected result:** Clear yes/no on whether WSL2 or a full VM can be used.

### Task 2: Choose first sandbox route

**Objective:** Pick the lowest-risk route for Lab 1.

**Recommended default:** WSL2 Ubuntu sandbox if virtualization can be enabled.

**Fallback:** Dedicated Ubuntu VM if WSL2 is unsuitable or Alejandro prefers snapshots over WSL.

**Avoid initially:** Docker Desktop on Windows, EVE-NG, GNS3 appliance, or direct host Docker.

### Task 3: Install only after approval

**Objective:** Install sandbox tooling in a reversible way.

**WSL2 route commands to plan, not execute yet:**

```powershell
# Elevated PowerShell after approval only
wsl --install -d Ubuntu
wsl --set-default-version 2
```

Inside Ubuntu after setup:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
# Container runtime choice to be confirmed: Docker Engine inside WSL or Podman.
```

**VM route actions to plan, not execute yet:**

1. Install a selected open virtualization platform.
2. Create Ubuntu LTS VM.
3. Allocate conservatively:
   - CPU: 2-4 vCPU.
   - RAM: 4-6 GB.
   - Disk: 40-80 GB, preferably on `E:` if performance is acceptable and space is desired.
4. Snapshot before installing lab tools.

### Task 4: Verify Lynjax lab in sandbox

**Objective:** Prove the repo lab works outside GitHub Actions.

**Commands:**

```bash
git clone https://github.com/Nstalej/lynjax.git
cd lynjax
bash scripts/lab_validate.sh
bash scripts/lab_up.sh
bash scripts/lab_smoke.sh
bash scripts/lab_down.sh
```

**Expected result:** Same behavior as CI: lab comes up, endpoints respond, lab tears down.

### Task 5: Add Containerlab only after Lab 1 passes

**Objective:** Prepare the next lab level without blocking local beta.

**Files to create later:**

- `lab/containerlab/README.md`
- `lab/containerlab/topologies/basic-lan.clab.yml`
- `scripts/containerlab_validate.sh`

**Acceptance criteria:** Topology can start/stop and Lynjax can check at least HTTP/TCP/SSH-like targets.

---

## Open Risks

- BIOS/firmware virtualization may be disabled or not visible from current CIM output.
- WSL is not currently installed, so WSL2 route requires Windows feature changes and likely admin elevation.
- Windows Home does not provide the full Hyper-V management stack, so some VM/lab options may differ from Windows Pro.
- Docker Desktop is intentionally not the first choice because Alejandro asked not to install Docker directly on the PC.
- Containerlab on Windows is best treated as Linux-inside-WSL/VM, not native Windows.
- EVE-NG and GNS3 may require larger downloads, more RAM, nested virtualization, and images that should not be mixed into the public repo.

---

## Recommendation

Proceed in this order:

1. Keep PR #2 lab baseline as the public reproducible source of truth.
2. Ask Alejandro to confirm whether BIOS virtualization can be enabled/verified.
3. Use WSL2 Ubuntu as the first sandbox if available.
4. If WSL2 is not suitable, use a dedicated Ubuntu VM with snapshots.
5. Run the existing Compose lab locally inside the sandbox.
6. Only then add Containerlab.
7. Leave GNS3/EVE-NG for a later evaluation PR.
