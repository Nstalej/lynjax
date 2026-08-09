"""Device inventory and live diagnostics.

The probe and audit endpoints are the first in Lynjax that can reach real
infrastructure. Both go through the connector factory, which refuses to build
anything unless the operator has explicitly enabled ``authorized-targets``. A
refusal surfaces as 403 rather than 500: it is a deliberate policy decision, not
a fault.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Response, status

from lynjax.core.deps import DeviceRepositoryDep, SettingsDep, VaultDep
from lynjax.schemas.devices import (
    AuditCheckResponse,
    ConnectivityCheckResponse,
    DeviceAuditResponse,
    DeviceCreateRequest,
    DeviceResponse,
)
from lynjax.services.connector_factory import (
    ConnectorNotAvailableError,
    MissingCredentialError,
    NetworkAccessDeniedError,
    build_connector,
)
from lynjax.services.connectors.base import ConnectorError
from lynjax.services.devices import (
    Device,
    DeviceNotFoundError,
    DuplicateDeviceError,
)

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _to_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        name=device.name,
        host=device.host,
        port=device.effective_port,
        connector_type=device.connector_type,
        device_type=device.device_type,
        credential_name=device.credential_name,
        description=device.description,
        is_active=device.is_active,
        status=device.status,
        last_seen=device.last_seen,
    )


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    repo: DeviceRepositoryDep, active_only: bool = False
) -> list[DeviceResponse]:
    return [_to_response(device) for device in await repo.list(active_only=active_only)]


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DeviceCreateRequest, repo: DeviceRepositoryDep
) -> DeviceResponse:
    try:
        device = await repo.create(**payload.model_dump())
    except DuplicateDeviceError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _to_response(device)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int, repo: DeviceRepositoryDep) -> DeviceResponse:
    try:
        return _to_response(await repo.get(device_id))
    except DeviceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_device(device_id: int, repo: DeviceRepositoryDep) -> Response:
    try:
        await repo.delete(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _resolve_connector(
    device_id: int, repo: DeviceRepositoryDep, vault: VaultDep, settings: SettingsDep
) -> tuple[Device, object]:
    try:
        device = await repo.get(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    try:
        connector = await build_connector(device, vault, settings)
    except NetworkAccessDeniedError as exc:
        # Deliberate policy, not a failure: 403 with the remedy in the body.
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except (ConnectorNotAvailableError, MissingCredentialError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return device, connector


@router.post("/{device_id}/check", response_model=ConnectivityCheckResponse)
async def check_device(
    device_id: int,
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    settings: SettingsDep,
) -> ConnectivityCheckResponse:
    """Probe one device and record the resulting status."""
    device, connector = await _resolve_connector(device_id, repo, vault, settings)

    try:
        result = await connector.test_connection()
    finally:
        await connector.disconnect()

    await repo.update_status(
        device.id, "online" if result.success else "offline", seen=result.success
    )

    return ConnectivityCheckResponse(
        device_id=device.id,
        device_name=device.name,
        host=device.host,
        reachable=result.success,
        latency_ms=round(result.latency_ms, 2),
        error=result.error_message,
    )


@router.post("/{device_id}/audit", response_model=DeviceAuditResponse)
async def audit_device(
    device_id: int,
    repo: DeviceRepositoryDep,
    vault: VaultDep,
    settings: SettingsDep,
) -> DeviceAuditResponse:
    """Collect state from one device and return its checks."""
    device, connector = await _resolve_connector(device_id, repo, vault, settings)

    try:
        await connector.connect()
        result = await connector.run_audit()
    except ConnectorError as exc:
        await repo.update_status(device.id, "offline")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    finally:
        await connector.disconnect()

    worst = result.worst_status
    await repo.update_status(
        device.id, "warning" if worst != "pass" else "online", seen=True
    )

    return DeviceAuditResponse(
        device_id=device.id,
        device_name=device.name,
        host=device.host,
        collected_at=result.timestamp.isoformat(),
        overall_status=worst,
        summary=result.summary,
        checks=[AuditCheckResponse(**asdict(check)) for check in result.checks],
    )
