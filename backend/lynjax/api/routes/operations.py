"""Endpoints the operator console needs.

These exist because the interface asked for them and they were missing: the
device detail tabs had no source of raw tables, the audit history had nowhere to
read from, the credential dialog had no API behind it, the settings log viewer
had nothing to read, and the dashboard had no aggregate to show.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response, status
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
from lynjax.services.agents import AgentNotFoundError, AgentRepository
from lynjax.services.assessment import collect_device
from lynjax.services.audit import NetworkSnapshot
from lynjax.services.audits import AuditNotFoundError, AuditRepository
from lynjax.services.connector_factory import (
    ConnectorNotAvailableError,
    MissingCredentialError,
    NetworkAccessDeniedError,
)
from lynjax.services.devices import DeviceNotFoundError
from lynjax.services.topology import build_topology
from lynjax.services.vault import CredentialNotFoundError, VaultError

logger = logging.getLogger("lynjax.api.operations")

router = APIRouter(prefix="/api/v1", tags=["operations"])


# ─── Device data: the detail tabs ───


@router.get("/devices/{device_id}/data")
async def device_data(
    device_id: int,
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    settings: SettingsDep,
    _user: OperatorDep,
) -> dict[str, Any]:
    """Everything one device reports: system, interfaces, ARP, MAC, routes.

    The audit endpoint returns verdicts; this returns the tables themselves,
    which is what a technician looking at a switch actually wants to read.
    """
    try:
        device = await repo.get(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        snapshot = await collect_device(device, vault, settings)
    except NetworkAccessDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except (ConnectorNotAvailableError, MissingCredentialError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    await repo.update_status(
        device.id,
        "offline" if snapshot.error else ("warning" if snapshot.is_empty else "online"),
        seen=not snapshot.error and not snapshot.is_empty,
    )

    return {
        "device": {
            "id": device.id,
            "name": device.name,
            "host": device.host,
            "connector_type": device.connector_type,
            "device_type": device.device_type,
        },
        # Reported rather than swallowed: a tab full of empty tables and no
        # explanation is how a broken collection looks like a healthy device.
        "error": snapshot.error,
        "collected": not snapshot.is_empty,
        "system": snapshot.system_info,
        "interfaces": [asdict(item) for item in snapshot.interfaces],
        "arp": [asdict(item) for item in snapshot.arp],
        "mac": [asdict(item) for item in snapshot.macs],
        "routes": [asdict(item) for item in snapshot.routes],
    }


# ─── Audit history ───


@router.get("/audits")
async def list_audits(
    db: DatabaseDep,
    _user: ViewerDep,
    audit_type: str | None = None,
    verdict: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    records = await AuditRepository(db).list(
        audit_type=audit_type, verdict=verdict, limit=limit
    )
    return [record.as_dict() for record in records]


@router.get("/audits/{audit_id}")
async def get_audit(audit_id: int, db: DatabaseDep, _user: ViewerDep) -> dict[str, Any]:
    try:
        record, payload = await AuditRepository(db).get(audit_id)
    except AuditNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    return {**record.as_dict(), "payload": payload}


# ─── Dashboard ───


@router.get("/dashboard")
async def dashboard(
    repo: DeviceRepositoryDep, db: DatabaseDep, settings: SettingsDep, _user: ViewerDep
) -> dict[str, Any]:
    """Aggregates for the operator's first screen."""
    devices = await repo.list()
    audits = AuditRepository(db)
    agents = await AgentRepository(db).list()

    by_status: dict[str, int] = {"online": 0, "offline": 0, "warning": 0, "unknown": 0}
    for device in devices:
        by_status[device.status] = by_status.get(device.status, 0) + 1

    # A health score is only meaningful once something has been polled; showing
    # 100% for an inventory nobody has checked would be a lie by omission.
    checked = len(devices) - by_status["unknown"]
    health = round(100 * by_status["online"] / checked) if checked else None

    return {
        "devices": {
            "total": len(devices),
            "active": sum(1 for device in devices if device.is_active),
            "by_status": by_status,
        },
        "health_score": health,
        "health_basis": (
            f"{by_status['online']} of {checked} checked device(s) responding"
            if checked
            else "No device has been checked yet"
        ),
        "agents": {
            "total": len(agents),
            "online": sum(1 for agent in agents if agent.status == "online"),
        },
        "audits": {
            "by_verdict": await audits.counts_by_verdict(),
            "recent": await audits.recent_activity(limit=8),
        },
        "network_policy": settings.network_policy,
    }


# ─── Topology ───


@router.get("/topology")
async def topology(
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    settings: SettingsDep,
    _user: OperatorDep,
    include_endpoints: bool = True,
) -> dict[str, Any]:
    """Build the map from live collection across the inventory."""
    try:
        snapshot = NetworkSnapshot()
        for device in await repo.list(active_only=True):
            try:
                snapshot.devices.append(await collect_device(device, vault, settings))
            except Exception as exc:  # noqa: BLE001 - one device must not blank the map
                logger.warning("Skipping %s in topology: %s", device.name, exc)
    except NetworkAccessDeniedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc

    return build_topology(snapshot, include_endpoints=include_endpoints).as_dict()


# ─── Credentials ───


class CredentialRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="ssh", max_length=32)
    data: dict[str, Any]


@router.get("/credentials")
async def list_credentials(vault: VaultDep, _user: OperatorDep) -> list[dict[str, Any]]:
    """Metadata only. Listing is routine and must never put secrets in memory."""
    return await vault.list_metadata()


@router.post("/credentials", status_code=status.HTTP_201_CREATED)
async def store_credential(
    payload: CredentialRequest, vault: VaultDep, _user: OperatorDep
) -> dict[str, Any]:
    try:
        credential_id = await vault.store(payload.name, payload.type, payload.data)
    except VaultError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return {"id": credential_id, "name": payload.name, "type": payload.type}


@router.delete(
    "/credentials/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_credential(name: str, vault: VaultDep, _user: OperatorDep) -> Response:
    try:
        await vault.delete(name)
    except CredentialNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Agents ───


class AgentRegistration(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=255)
    agent_type: str = Field(default="windows_ad", max_length=50)
    version: str | None = None


@router.get("/agents")
async def list_agents(db: DatabaseDep, _user: ViewerDep) -> list[dict[str, Any]]:
    return [agent.as_dict() for agent in await AgentRepository(db).list()]


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def register_agent(
    payload: AgentRegistration, db: DatabaseDep, _user: OperatorDep
) -> dict[str, Any]:
    agent = await AgentRepository(db).register(**payload.model_dump())
    return agent.as_dict()


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str, db: DatabaseDep, _user: OperatorDep
) -> dict[str, Any]:
    try:
        return (await AgentRepository(db).heartbeat(agent_id)).as_dict()
    except AgentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete(
    "/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_agent(agent_id: str, db: DatabaseDep, _admin: AdminDep) -> Response:
    try:
        await AgentRepository(db).delete(agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── System logs ───


@router.get("/logs")
async def system_logs(
    settings: SettingsDep,
    _admin: AdminDep,
    lines: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    """Tail the log file, so the audit trail is visible without shell access."""
    log_file = settings.log_file

    if not log_file.exists():
        return {
            "path": str(log_file),
            "lines": [],
            "note": "No log file yet. It is created when the server starts.",
        }

    try:
        content = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Cannot read the log: {exc}"
        ) from exc

    return {"path": str(log_file), "lines": content[-lines:], "note": None}
