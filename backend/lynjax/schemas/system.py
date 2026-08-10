"""System metadata returned by the info endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class InfoResponse(BaseModel):
    name: str
    version: str
    environment: str
    network_policy: str
