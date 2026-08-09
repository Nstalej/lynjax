"""Request and response models for the device and diagnostic endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ConnectorType = Literal["ssh", "snmp", "rest"]


class DeviceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=255)
    connector_type: ConnectorType
    device_type: str = Field(default="auto", max_length=50)
    port: int | None = Field(default=None, ge=1, le=65535)
    credential_name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class DeviceResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    connector_type: str
    device_type: str
    credential_name: str | None
    description: str | None
    is_active: bool
    status: str
    last_seen: str | None


class ConnectivityCheckResponse(BaseModel):
    """Result of probing one device."""

    device_id: int
    device_name: str
    host: str
    reachable: bool
    latency_ms: float | None = None
    error: str | None = None


class AuditCheckResponse(BaseModel):
    name: str
    status: str
    message: str
    details: dict | None = None


class DeviceAuditResponse(BaseModel):
    device_id: int
    device_name: str
    host: str
    collected_at: str
    overall_status: str
    summary: str
    checks: list[AuditCheckResponse]
