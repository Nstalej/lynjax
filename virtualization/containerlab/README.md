# Lynjax Containerlab Artifacts

This directory contains sanitized Containerlab preparation artifacts for the Lynjax v1.0 test candidate.

## Files

- `lynjax-demo.clab.yml` — minimal, non-sensitive topology for visual inspection and future Linux runtime deployment.

## Safety

- Do not deploy this topology on Windows/Git Bash.
- Deploy only inside WSL2 Ubuntu/Debian, a disposable Ubuntu VM, or CI where Docker and Containerlab are intentionally installed.
- Do not add real customer IPs, credentials, configs, packet captures, or external targets.
- Keep the topology demo-only and isolated.

## Static validation from the repo root

```bash
bash scripts/lab_validate.sh
```

This checks that the topology artifact exists and contains expected sanitized Containerlab structure without requiring Docker or Containerlab.

## Future runtime commands inside Linux only

```bash
# From repo root
containerlab inspect --topo virtualization/containerlab/lynjax-demo.clab.yml || true

# Deploy only after confirming Docker/Containerlab are available in the Linux runtime
sudo containerlab deploy --topo virtualization/containerlab/lynjax-demo.clab.yml
sudo containerlab inspect --topo virtualization/containerlab/lynjax-demo.clab.yml
sudo containerlab destroy --topo virtualization/containerlab/lynjax-demo.clab.yml --cleanup
```

See `../../docs/lab/CONTAINERLAB_PREP.md` for the full Day 4 preparation notes.
