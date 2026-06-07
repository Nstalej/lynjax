# Lynjax Local Lab

This folder contains the first safe lab baseline for Lynjax beta 0.5.

The goal is to make Day 5 practical: by the time backend, frontend and reporting are wired together, there is already a deterministic local environment that can be started without touching real infrastructure.

## Safety boundaries

- The lab is local-only and demo-focused.
- It does not scan external networks.
- It does not include real credentials.
- It does not model client infrastructure.
- It uses sanitized fixtures under `lab/sample-data/`.

## Included targets

The initial Docker Compose lab defines two simple HTTP services:

- `target-web`: an nginx target with a Lynjax demo page.
- `target-metadata`: a Python HTTP server exposing static metadata JSON.

These are intentionally boring. The first goal is repeatability for connectivity, HTTP status and evidence/report fixtures.

## Commands

From the repository root:

```bash
# Validate lab files and compose syntax when Docker Compose is available
bash scripts/lab_validate.sh

# Start the lab
bash scripts/lab_up.sh

# Start, probe and tear down the lab automatically
bash scripts/lab_smoke.sh

# Stop and remove lab containers
bash scripts/lab_down.sh
```

After starting the lab, expected local URLs are:

- `http://localhost:18080/` → target web landing page
- `http://localhost:18081/metadata.json` → target metadata fixture

## Fixture files

- `lab/sample-data/assessment-scope.json`: authorized demo scope.
- `lab/sample-data/targets.json`: safe targets for the demo lab.
- `lab/sample-data/expected-checks.json`: initial checks that future backend/report code should support.

## CI smoke behavior

`Lab CI` validates the fixtures, runs `docker compose config`, starts the lab, probes both HTTP endpoints, and tears the lab down automatically.

## Future lab expansion

After the beta flow is stable, possible additions are:

1. TCP port-check target.
2. SSH service with disposable demo credentials generated at runtime.
3. SNMP simulator/container.
4. Containerlab/GNS3/EVE-NG exploration only after the simple Docker lab is stable.
