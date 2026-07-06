# Lynjax

**Intelligent Network Visibility**

Lynjax is the clean rebrand and beta 0.5 foundation for the former NetVault concept: a local-first network assessment tool focused on authorized audits, traceability, evidence and technical reporting.

## Product direction

Lynjax is not a generic monitoring clone. The first beta should be small, stable and useful for real technical assessments:

- define an authorized assessment scope;
- register devices and credentials provided by the client;
- run basic connectivity, TCP, SSH and later SNMP checks;
- keep traceable evidence;
- generate a clear technical report;
- purge sensitive data after the assessment.

## Brand line

```text
Lynjax — Intelligent Network Visibility
```

Extended description:

```text
Intelligent network audit, assessment and traceability for real infrastructure.
```

## Repository status

This folder starts as the clean Lynjax workspace. The old NetVault repository remains a historical reference. Do not copy code wholesale; migrate only verified concepts, tests, smoke checks and components that fit the new architecture.

## Initial structure

```text
backend/              Future FastAPI app
frontend/             Future landing/dashboard shell
labs/local-demo/      Docker/local demo lab
assets/logo/          SVG logo and marks
assets/brand/         Brand exports and visual references
docs/branding/        Brand strategy, DESIGN.md notes, copy
docs/architecture/    Technical architecture decisions
docs/field-assessment/Authorized assessment workflow
docs/guides/          Setup and operator guides
docs/plans/           Implementation plans
scripts/              Smoke checks and utilities
data/                 Local runtime data, ignored later
reports/              Generated reports, ignored later
```

## Immediate next step

Build the brand kit and beta 0.5 skeleton before migrating backend code.
