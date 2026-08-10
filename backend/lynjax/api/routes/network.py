"""Discovery, network audit, chain tracing and report download.

Every endpoint here can reach real infrastructure, so all of them go through
the same policy gate and surface a refusal as 403 rather than 500.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from lynjax.core.deps import (
    AdminDep,
    DatabaseDep,
    DeviceRepositoryDep,
    OperatorDep,
    SettingsDep,
    VaultDep,
    ViewerDep,
)
from lynjax.services.agents import AgentRepository
from lynjax.services.assessment import render_markdown, run_assessment
from lynjax.services.audit import run_network_audit
from lynjax.services.audits import AuditRepository
from lynjax.services.connector_factory import NetworkAccessDeniedError
from lynjax.services.discovery import (
    DiscoveryError,
    DiscoveryService,
    summarise,
)
from lynjax.services.reports.store import ReportStore

logger = logging.getLogger("lynjax.api.network")

router = APIRouter(prefix="/api/v1", tags=["network"])

#: One service per process. Jobs live in memory, so they do not survive a
#: restart; that is acceptable for a field tool and honest about what it is.
_discovery = DiscoveryService()


class DiscoveryRequest(BaseModel):
    subnets: list[str] = Field(..., min_length=1, max_length=16)
    methods: list[str] | None = None
    max_hosts: int = Field(default=4096, ge=1, le=65536)
    allow_public: bool = False
    snmp_community: str | None = None


class AuditRequest(BaseModel):
    client: str = ""
    trace_target: str | None = None
    locale: str = Field(default="es", pattern="^(es|en)$")


class CheckResponse(BaseModel):
    name: str
    status: str
    message: str
    details: dict | None = None


def _deny(exc: NetworkAccessDeniedError) -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, str(exc))


@router.post("/discovery", status_code=status.HTTP_202_ACCEPTED)
async def start_discovery(
    payload: DiscoveryRequest,
    repo: DeviceRepositoryDep,
    settings: SettingsDep,
    _user: OperatorDep,
) -> dict:
    """Start a background scan of an authorised scope."""
    _discovery._repo = repo

    try:
        job_id = await _discovery.start(
            payload.subnets,
            settings,
            methods=payload.methods,
            max_hosts=payload.max_hosts,
            allow_public=payload.allow_public,
            snmp_community=payload.snmp_community,
        )
    except NetworkAccessDeniedError as exc:
        raise _deny(exc) from exc
    except DiscoveryError as exc:
        # A refused scope is the caller's mistake, not a server fault.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    job = await _discovery.get_job(job_id)
    return summarise(job)


@router.get("/discovery")
async def list_discovery_jobs(_user: ViewerDep) -> list[dict]:
    return [summarise(job) for job in await _discovery.list_jobs()]


@router.get("/discovery/{job_id}")
async def get_discovery_job(job_id: str, _user: ViewerDep) -> dict:
    job = await _discovery.get_job(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No job {job_id!r}")
    return summarise(job)


@router.delete("/discovery/{job_id}", status_code=status.HTTP_202_ACCEPTED)
async def cancel_discovery_job(job_id: str, _user: OperatorDep) -> dict:
    if not await _discovery.cancel(job_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Job {job_id!r} is not running, so there is nothing to cancel.",
        )
    return {"job_id": job_id, "status": "cancelled"}


@router.post("/audit")
async def run_audit(
    payload: AuditRequest,
    request: Request,
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    settings: SettingsDep,
    db: DatabaseDep,
    _user: OperatorDep,
) -> dict:
    """Collect from every active device, analyse, and keep the result.

    The rendered report is cached on the app so it can be downloaded without
    re-running the collection, which would hit the client's network twice for
    one deliverable.
    """
    try:
        assessment = await run_assessment(
            repo,
            vault,
            settings,
            client=payload.client,
            trace_target=payload.trace_target,
        )
    except NetworkAccessDeniedError as exc:
        raise _deny(exc) from exc

    _report_store(request).add(assessment.assessment_id, assessment, payload.locale)

    body = _audit_payload(assessment, payload.locale)

    # Persisted as well as held: the in-memory copy makes the immediate download
    # cheap, and the stored row is what the history screen reads after a restart.
    await AuditRepository(db).save(
        assessment_id=assessment.assessment_id,
        payload=body,
        client=payload.client or None,
        audit_type="trace" if payload.trace_target else "network",
        verdict=assessment.verdict,
        checks_total=len(assessment.findings),
        issues_total=sum(1 for check in assessment.findings if check.status != "pass"),
        summary=assessment.summarise(payload.locale),
        locale=payload.locale,
        started_at=assessment.started_at,
        completed_at=assessment.completed_at,
    )

    return body


def _audit_payload(assessment, locale: str) -> dict:
    return {
        "assessment_id": assessment.assessment_id,
        "client": assessment.client,
        "started_at": assessment.started_at.isoformat(),
        "verdict": assessment.verdict,
        "summary": assessment.summarise(locale),
        "devices_assessed": len(assessment.snapshot.devices),
        "unreachable": [
            {"device": name, "reason": reason}
            for name, reason in assessment.unreachable
        ],
        "findings": [asdict(check) for check in assessment.findings],
        "trace": _trace_payload(assessment.trace) if assessment.trace else None,
        "report_url": f"/api/v1/reports/{assessment.assessment_id}",
    }


def _report_store(request: Request) -> ReportStore:
    store = getattr(request.app.state, "reports", None)
    if store is None:
        store = ReportStore()
        request.app.state.reports = store
    return store


def _trace_payload(trace) -> dict:
    return {
        "target": trace.target,
        "resolved_mac": trace.resolved_mac,
        "verdict": trace.verdict,
        "summary": trace.summary,
        "hops": [
            {
                "role": hop.role,
                "name": hop.name,
                "host": hop.host,
                "device_id": hop.device_id,
                "port": hop.port,
                "evidence": hop.evidence,
                "findings": [asdict(check) for check in hop.findings],
            }
            for hop in trace.hops
        ],
        "findings": [asdict(check) for check in trace.findings],
    }


@router.get("/reports/{assessment_id}")
async def download_report(
    assessment_id: str,
    request: Request,
    _user: ViewerDep,
    fmt: str = Query(default="md", pattern="^(md|pdf)$"),
) -> Response:
    """Download a report produced by a previous audit."""
    entry = _report_store(request).get(assessment_id)
    if entry is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No report for {assessment_id!r}. Reports are held in memory and "
            f"do not survive a restart; run the audit again.",
        )

    assessment, locale = entry
    markdown = render_markdown(assessment, locale)

    if fmt == "md":
        return Response(
            markdown,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{assessment_id}.md"'
            },
        )

    try:
        from lynjax.services.pdf import markdown_to_pdf
    except ImportError as exc:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "PDF support is not installed. Install with: pip install 'lynjax[pdf]'",
        ) from exc

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{assessment_id}.pdf"
        markdown_to_pdf(markdown, path)
        payload = path.read_bytes()

    return Response(
        payload,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{assessment_id}.pdf"'},
    )


@router.post("/trace/{target_ip}")
async def trace_endpoint(
    target_ip: str,
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    settings: SettingsDep,
    _user: OperatorDep,
) -> dict:
    """Trace one endpoint from its access port out to the edge.

    The answer to "this machine is slow": which link in its path is at fault.
    """
    try:
        assessment = await run_assessment(repo, vault, settings, trace_target=target_ip)
    except NetworkAccessDeniedError as exc:
        raise _deny(exc) from exc

    if assessment.trace is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "The trace produced no result."
        )

    return _trace_payload(assessment.trace)


@router.get("/audit/findings")
async def network_findings(
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    settings: SettingsDep,
    _user: OperatorDep,
) -> list[CheckResponse]:
    """Cross-device findings only, without producing a report."""
    try:
        assessment = await run_assessment(repo, vault, settings)
    except NetworkAccessDeniedError as exc:
        raise _deny(exc) from exc

    return [
        CheckResponse(**asdict(check))
        for check in run_network_audit(assessment.snapshot)
    ]


@router.post("/purge", status_code=status.HTTP_200_OK)
async def purge_client_data(
    request: Request,
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    db: DatabaseDep,
    _user: AdminDep,
) -> dict:
    """Remove every trace of a client's engagement.

    Devices, credentials and the reports held in memory. The CLI cannot reach
    that last group — it runs in a different process — so a technician who ran
    `lynjax purge` against a live server still had device names, addresses and
    findings sitting in it. This is the one call that clears all three.
    """
    devices = await repo.purge_all()
    credentials = await vault.purge_all()
    reports = _report_store(request).purge()
    audits = await AuditRepository(db).purge_all()
    agents = await AgentRepository(db).purge_all()

    logger.warning(
        "Client data purged: %s device(s), %s credential(s), %s report(s), "
        "%s stored audit(s), %s agent(s)",
        devices,
        credentials,
        reports,
        audits,
        agents,
    )
    return {
        "devices_removed": devices,
        "credentials_removed": credentials,
        "reports_removed": reports,
        "audits_removed": audits,
        "agents_removed": agents,
    }
