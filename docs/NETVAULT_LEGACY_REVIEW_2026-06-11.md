# NetVault Legacy Review for Lynjax

**Date:** 2026-06-11  
**Purpose:** Extract useful product, visual, connectivity, Active Directory, MCP/LLM and roadmap ideas from the previous NetVault codebase and Word roadmap documents, without migrating the old codebase wholesale.

## Sources inspected

- Legacy repo: `C:/Users/nesal/Documents/001_Programas/netvault`
- Current Lynjax repo: `C:/Users/nesal/Documents/001_Programas/netvault-rebrand-lab/lynjax`
- Word roadmaps:
  - `C:/Users/nesal/Documents/002-Obsidian-Vault/01 - Proyectos/Network Monitor/NetVault_Roadmap_2025-2026.docx`
  - `C:/Users/nesal/Documents/002-Obsidian-Vault/01 - Proyectos/Network Monitor/NetVault_Roadmap_v2_i18n_AI.docx`
- Legacy memory/plan docs:
  - `netvault/Memory/memory.md`
  - `netvault/Memory/beta_0.2_status.md`
  - `netvault/docs/plans/2026-05-30-netvault-beta-technical-automation.md`

## Legacy NetVault baseline found

### Backend and core modules

NetVault already had several concepts that are worth preserving as requirements, but not copying blindly:

- FastAPI backend.
- SQLite/aiosqlite database layer.
- Device CRUD and device status model.
- Credential vault concept using encrypted storage.
- Device manager and audit engine concepts.
- Scheduler for periodic checks.
- Network connectors:
  - SNMP connector.
  - SSH connector.
  - REST API connector.
- Configured device inventory file examples for MikroTik, Sophos, Cisco and Windows AD.
- Agent registry and heartbeat endpoints.
- MCP server/tooling layer for AI-facing inspection.

### Frontend and visual modules

Legacy NetVault had a React/Vite frontend under `frontend/src` with:

- `App.jsx` with protected routes.
- `Layout`, `Sidebar`, `Topbar`.
- `LanguageSwitcher`.
- Auth context and protected route handling.
- Pages:
  - Dashboard.
  - Devices.
  - Device detail.
  - Audit.
  - Topology.
  - Settings.
  - Login.
- i18n folders:
  - `locales/en/*`
  - `locales/es/*`
- Data fetching using React Query.
- Icons through `lucide-react`.
- Role-aware UI based on Admin/Editor/Viewer.

The old UI was functionally useful but visually simpler. Lynjax should reuse the information architecture but redesign the experience around a more polished animated SaaS/dashboard interface.

## Active Directory capability found

NetVault had a Windows AD agent in `agents/windows_ad`.

### What it collected

The AD collector could query:

- Users.
- Groups.
- Computers.
- GPOs.
- Simplified DNS records.
- Placeholder areas for replication and DHCP.

Important collected fields included:

- User account name, display name, mail, department, title.
- Enabled/disabled status.
- Locked status.
- Last logon.
- Password-never-expires flag.
- Group membership.
- Computer hostname, OS, OS version and last logon.
- Group member counts and scope.
- GPO name/status/created date.

### Agent behavior

The AD agent could:

- Load `config.yml`.
- Register with the NetVault server.
- Send heartbeat.
- Run daily AD audit.
- Send audit results to `/api/audit/results`.
- Use `X-Agent-Token` for agent authentication.
- Use NSSM as the preferred Windows Service wrapper.

### API support

Legacy routes included:

- `POST /api/agents/register`
- `POST /api/agents/{agent_id}/heartbeat`
- `GET /api/agents/{agent_id}/status`
- `GET /api/agents/{agent_id}/ad-data`
- `GET /api/agents/download/{agent_type}`

### Gap for Lynjax

Lynjax does not yet have this AD module. It should be planned as a later milestone, not in the first visual-only structure. However, the frontend navigation and data model should reserve space for it.

Recommended Lynjax future visual sections:

- Directory Overview.
- Users.
- Groups.
- Computers.
- GPOs.
- Risk Findings.
- AD Connector/Agent status.

## MCP / LLM capability found

NetVault had an MCP layer intended for LLM-facing network analysis.

### Legacy MCP tool concepts

The old MCP provider included tools or tool-like methods for:

- List devices.
- Get device details.
- Get interfaces.
- Get ARP table.
- Get MAC table.
- Run audit.
- Get audit history.
- Get network topology.
- Get alerts.
- Search by MAC.
- Search by IP.
- Retrieve AD users/groups/GPO placeholders.

### Roadmap AI phases from Word docs

The Word roadmap planned AI in three phases:

1. **v1.0 Report Agent**
   - Claude API.
   - Read-only.
   - Generate PDF analysis in ES/EN.
   - Use only aggregated metrics, not sensitive IPs/hostnames.

2. **v1.5 Diagnostic Agent**
   - Claude API + MCP read-only tools.
   - Chat UI for natural-language network questions.
   - No execution.

3. **v2.0 Network Intelligence**
   - MCP action tools.
   - Human-in-the-loop approval.
   - Actions like VLANs, ACLs, port/service restart, quarantine.
   - Full audit log.

### Gap for Lynjax

For Lynjax, this should become a future **LLM Connector / Intelligence Layer** rather than immediate implementation. The visual structure should include a disabled/planned module for:

- AI Reports.
- Diagnostic Assistant.
- MCP/LLM connector settings.
- Approval queue for future HITL actions.
- Audit log of recommendations/actions.

## Word roadmap summary

### Original roadmap 2025-2026

Planned tiers:

- v0.1 Alpha: basic audit, ping/TCP/HTTP/SSH, dashboard, SQLite.
- v0.5 Lite: JWT roles, SNMP IF-MIB, email/Telegram alerts, manual topology, SQLite.
- v1.0 Standard: LLDP/ARP discovery, real-time topology, UniFi/Ruckus, TimescaleDB, reports.
- v1.5 Pro: Proxmox/VMware, anomaly detection, multi-tenant, LDAP/AD.
- v2.0 Ultra: Celery/Redis polling, Grafana/SIEM, public API, agents, marketplace.

### Roadmap v2 i18n + AI

Added:

- ES/EN i18n from v0.5.
- Report Agent in v1.0.
- Diagnostic Agent with MCP in v1.5.
- Network Intelligence actions with HITL in v2.0.
- Rule: no hardcoded UI strings in React; use i18n keys.

## What Lynjax should reuse

Reuse as product requirements and UI modules:

1. Device inventory and device detail model.
2. Connectivity checks: ping/TCP/HTTP/SSH first; SNMP later.
3. Audit results and evidence trail.
4. Report generation in Markdown/LaTeX/PDF.
5. i18n ES/EN from the start.
6. Sidebar + topbar dashboard structure.
7. Role-aware future architecture, even if auth is deferred.
8. AD connector/agent as a planned module.
9. MCP/LLM read-only reporting as a planned module.
10. Topology visual placeholder now, Cytoscape/manual topology later.

## What Lynjax should not copy directly yet

Avoid direct migration of:

- Large legacy modules without tests/contract review.
- Old auth/RBAC until the visual and assessment flow stabilizes.
- Old credential vault until a safe field-beta model is defined.
- Real SNMP/AD/SSH execution in the visual sprint.
- HITL action tools before read-only reporting and audit logging are solid.

## Proposed Lynjax module map

### Immediate visual structure

- Overview.
- Assets.
- Connectivity.
- Assessments.
- Evidence.
- Reports.
- Topology.
- Directory / Active Directory placeholder.
- Intelligence / LLM placeholder.
- Settings.

### Frontend visual requirements

- Animated collapsible sidebar.
- Mobile drawer sidebar.
- Topbar with language switcher.
- Modular cards with status/risk/evidence counts.
- Dedicated empty states for modules not connected yet.
- Skeleton/loading states for future backend calls.
- `prefers-reduced-motion` support.
- No hardcoded strings outside i18n files.

### Backend-ready contracts to design later

- `AssessmentRequest` / `AssessmentResult`.
- `Asset` / `AssetDetail`.
- `ConnectivityCheck`.
- `EvidenceItem`.
- `ReportArtifact`.
- `DirectorySnapshot`.
- `AgentStatus`.
- `LLMReportRequest` / `LLMReportResult`.

## Suggested phased roadmap for Lynjax

### Phase A — Visual platform shell

Goal: Build the modern SaaS-like structure before connecting deeper functionality.

Deliverables:

- Animated sidebar/topbar layout.
- ES/EN i18n.
- Route structure for all planned modules.
- Mock cards/tables/states aligned with Lynjax branding.
- Clear visual placeholders for AD and LLM modules.

### Phase B — End-to-end assessment demo

Goal: Connect the visual shell to the current safe backend endpoint.

Deliverables:

- Frontend action calls backend connectivity demo.
- Results render in Connectivity/Assessment views.
- Markdown report generated from returned data.
- Evidence fields shown in UI.

### Phase C — Persistence and evidence

Goal: Store executions and support cleanup.

Deliverables:

- Local SQLite persistence.
- Execution history.
- Evidence list.
- Data purge/sanitization workflow.

### Phase D — AD connector planning/prototype

Goal: Reintroduce AD safely as a controlled connector.

Deliverables:

- AD visual pages.
- Agent status view.
- AD data schema.
- Sanitized demo data first.
- Later Windows AD agent integration.

### Phase E — LLM/MCP planning/prototype

Goal: Start with read-only report intelligence.

Deliverables:

- LLM connector settings placeholder.
- AI report generation design.
- Prompt/data minimization rules.
- Later MCP read-only tools.

## Immediate conclusion

The next build should prioritize the Lynjax visual shell with i18n and modern animated navigation. While doing that, include the route/menu architecture for legacy NetVault capabilities: Devices, Connectivity, Topology, Directory/AD, Reports and Intelligence. This avoids redesign later when frontend/backend functionality becomes active.
