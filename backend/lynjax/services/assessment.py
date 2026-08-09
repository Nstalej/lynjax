"""Assessment orchestration and reporting.

One run collects from every registered device, applies the cross-device checks,
optionally traces one endpoint's chain, and renders a report.

The report is the deliverable. Everything else in Lynjax is instrumentation for
producing it, so it is written to be handed to a client unedited: findings
ordered by severity, each one saying what was observed and what to do, and an
explicit statement of what was *not* covered.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from lynjax.core.config import APP_VERSION, Settings
from lynjax.services.audit import (
    ChainTrace,
    DeviceSnapshot,
    NetworkSnapshot,
    run_network_audit,
    trace_chain,
)
from lynjax.services.connector_factory import build_connector
from lynjax.services.connectors.base import AuditCheck, ConnectorError, utc_now
from lynjax.services.devices import DeviceRepository
from lynjax.services.vault import CredentialVault

logger = logging.getLogger("lynjax.assessment")

Locale = Literal["es", "en"]

SEVERITY_ORDER = {"fail": 0, "warning": 1, "pass": 2}

LABELS: dict[Locale, dict[str, str]] = {
    "es": {
        "title": "Informe de auditoría de red",
        "client": "Cliente",
        "generated": "Generado",
        "tool": "Herramienta",
        "scope": "Alcance evaluado",
        "summary": "Resumen ejecutivo",
        "devices": "Dispositivos revisados",
        "findings": "Hallazgos",
        "chain": "Traza de conexión",
        "evidence": "Evidencia técnica",
        "limits": "Alcance no cubierto",
        "next": "Próximos pasos",
        "device": "Dispositivo",
        "host": "Dirección",
        "status": "Estado",
        "model": "Modelo",
        "no_findings": "No se encontraron hallazgos en los chequeos aplicados.",
        "severity": {"fail": "Crítico", "warning": "Atención", "pass": "Correcto"},
        "hop": "Salto",
        "role": "Rol",
        "port": "Puerto",
        "evidence_col": "Evidencia",
        "unreachable": "No alcanzado",
        "no_data": "Sin datos",
    },
    "en": {
        "title": "Network audit report",
        "client": "Client",
        "generated": "Generated",
        "tool": "Tool",
        "scope": "Assessed scope",
        "summary": "Executive summary",
        "devices": "Devices reviewed",
        "findings": "Findings",
        "chain": "Connection trace",
        "evidence": "Technical evidence",
        "limits": "Not covered",
        "next": "Next steps",
        "device": "Device",
        "host": "Address",
        "status": "Status",
        "model": "Model",
        "no_findings": "No findings were raised by the checks that ran.",
        "severity": {"fail": "Critical", "warning": "Attention", "pass": "OK"},
        "hop": "Hop",
        "role": "Role",
        "port": "Port",
        "evidence_col": "Evidence",
        "unreachable": "Unreachable",
        "no_data": "No data",
    },
}


@dataclass
class Assessment:
    assessment_id: str
    client: str = ""
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    snapshot: NetworkSnapshot = field(default_factory=NetworkSnapshot)
    findings: list[AuditCheck] = field(default_factory=list)
    trace: ChainTrace | None = None
    unreachable: list[tuple[str, str]] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        statuses = {check.status for check in self.findings}
        if self.trace:
            statuses.add(self.trace.verdict)
        if "fail" in statuses:
            return "fail"
        if "warning" in statuses:
            return "warning"
        return "pass"

    @property
    def summary(self) -> str:
        return self.summarise("en")

    def summarise(self, locale: Locale = "es") -> str:
        critical = sum(1 for check in self.findings if check.status == "fail")
        warnings = sum(1 for check in self.findings if check.status == "warning")
        collected = sum(
            1 for snapshot in self.snapshot.devices if not snapshot.is_empty
        )
        silent = len(self.snapshot.devices) - collected

        if locale == "es":
            return (
                f"{len(self.snapshot.devices)} dispositivo(s) evaluado(s): "
                f"{collected} entregaron datos, {silent} no respondieron. "
                f"{critical} hallazgo(s) crítico(s) y {warnings} advertencia(s)."
            )
        return (
            f"{len(self.snapshot.devices)} device(s) assessed: {collected} returned "
            f"data, {silent} did not respond. {critical} critical finding(s) and "
            f"{warnings} warning(s)."
        )


async def collect_device(
    device, vault: CredentialVault, settings: Settings
) -> DeviceSnapshot:
    """Collect everything one device will report.

    A device that fails part-way keeps whatever it already gave us, with the
    error recorded. Partial data is still evidence; discarding it would hide
    what the device did manage to say.
    """
    snapshot = DeviceSnapshot(device=device)
    connector = await build_connector(device, vault, settings)

    try:
        await connector.connect()
        snapshot.system_info = await connector.get_system_info()
        snapshot.interfaces = await connector.get_interfaces()
        snapshot.arp = await connector.get_arp_table()
        snapshot.macs = await connector.get_mac_table()
        snapshot.routes = await connector.get_routes()
    except ConnectorError as exc:
        snapshot.error = str(exc)
        logger.warning("Collection from %s failed: %s", device.name, exc)
    finally:
        await connector.disconnect()

    return snapshot


async def run_assessment(
    repo: DeviceRepository,
    vault: CredentialVault,
    settings: Settings,
    *,
    client: str = "",
    trace_target: str | None = None,
) -> Assessment:
    """Collect from every active device and analyse the result."""
    started = utc_now()
    assessment = Assessment(
        assessment_id=f"assessment-{started.strftime('%Y%m%d-%H%M%S')}",
        client=client,
        started_at=started,
    )

    for device in await repo.list(active_only=True):
        try:
            snapshot = await collect_device(device, vault, settings)
        except Exception as exc:  # noqa: BLE001 - one bad device must not stop the run
            assessment.unreachable.append((device.name, str(exc)))
            logger.warning("Could not build a connector for %s: %s", device.name, exc)
            continue

        if snapshot.error:
            assessment.unreachable.append((device.name, snapshot.error))
        assessment.snapshot.devices.append(snapshot)

    assessment.findings = run_network_audit(assessment.snapshot)

    if trace_target:
        assessment.trace = trace_chain(assessment.snapshot, trace_target)

    assessment.completed_at = utc_now()
    return assessment


# ─── Reporting ───


def render_markdown(assessment: Assessment, locale: Locale = "es") -> str:
    """Render the assessment as a report meant to be handed over as-is."""
    text = LABELS.get(locale, LABELS["es"])
    lines: list[str] = []

    lines.append(f"# {text['title']}")
    lines.append("")
    if assessment.client:
        lines.append(f"**{text['client']}:** {assessment.client}  ")
    lines.append(
        f"**{text['generated']}:** "
        f"{assessment.started_at.strftime('%Y-%m-%d %H:%M UTC')}  "
    )
    lines.append(f"**{text['tool']}:** Lynjax {APP_VERSION}")
    lines.append("")

    lines.append(f"## {text['summary']}")
    lines.append("")
    lines.append(assessment.summarise(locale))
    lines.append("")

    lines.append(f"## {text['devices']}")
    lines.append("")
    lines.append(
        f"| {text['device']} | {text['host']} | {text['model']} | {text['status']} |"
    )
    lines.append("|---|---|---|---|")
    for snapshot in assessment.snapshot.devices:
        model = snapshot.system_info.get("model") or snapshot.system_info.get(
            "descr", "—"
        )
        if snapshot.error:
            status = text["unreachable"]
        elif snapshot.is_empty:
            status = text["no_data"]
        else:
            status = "OK"
        lines.append(
            f"| {snapshot.device.name} | {snapshot.device.host} | {model} | {status} |"
        )
    lines.append("")

    lines.append(f"## {text['findings']}")
    lines.append("")
    if not assessment.findings:
        lines.append(text["no_findings"])
    else:
        for check in sorted(
            assessment.findings, key=lambda c: SEVERITY_ORDER.get(c.status, 3)
        ):
            label = text["severity"].get(check.status, check.status)
            lines.append(f"### [{label}] {check.name}")
            lines.append("")
            lines.append(check.message)
            lines.append("")
    lines.append("")

    if assessment.trace:
        lines.append(f"## {text['chain']}")
        lines.append("")
        lines.append(f"`{assessment.trace.target}` → {assessment.trace.summary}")
        lines.append("")
        lines.append(
            f"| {text['hop']} | {text['role']} | {text['port']} | "
            f"{text['evidence_col']} |"
        )
        lines.append("|---|---|---|---|")
        for index, hop in enumerate(assessment.trace.hops, start=1):
            lines.append(
                f"| {index} | {hop.role} — {hop.name} | {hop.port or '—'} | "
                f"{hop.evidence} |"
            )
        lines.append("")
        for hop in assessment.trace.hops:
            for check in hop.findings:
                if check.status == "pass":
                    continue
                label = text["severity"].get(check.status, check.status)
                lines.append(f"- **[{label}] {hop.name}:** {check.message}")
        lines.append("")

    lines.append(f"## {text['limits']}")
    lines.append("")
    if assessment.unreachable:
        for name, reason in assessment.unreachable:
            lines.append(f"- {name}: {reason}")
    else:
        lines.append("—")
    lines.append("")

    return "\n".join(lines)


def write_report(assessment: Assessment, path: Path, *, locale: Locale = "es") -> Path:
    """Write the report. A ``.pdf`` suffix renders PDF, anything else Markdown."""
    markdown = render_markdown(assessment, locale)

    if path.suffix.lower() == ".pdf":
        return _write_pdf(markdown, path)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def _write_pdf(markdown: str, path: Path) -> Path:
    """Render Markdown to PDF, falling back to Markdown when unavailable.

    PDF rendering needs an optional dependency. Failing the whole audit because
    a rendering library is missing would throw away the collected evidence, so
    the Markdown is written next to it and the caller is told.
    """
    try:
        from lynjax.services.pdf import markdown_to_pdf
    except ImportError:
        fallback = path.with_suffix(".md")
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback.write_text(markdown, encoding="utf-8")
        logger.warning(
            "PDF support is not installed; wrote %s instead. "
            "Install with: pip install 'lynjax[pdf]'",
            fallback,
        )
        return fallback

    path.parent.mkdir(parents=True, exist_ok=True)
    markdown_to_pdf(markdown, path)
    return path
