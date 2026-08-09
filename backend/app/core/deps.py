"""FastAPI dependencies.

Everything the routes need is resolved through these, so tests can override any
one of them without touching application state or the filesystem.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.database import Database
from app.services.devices import DeviceRepository
from app.services.vault import CredentialVault


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_vault(request: Request) -> CredentialVault:
    return request.app.state.vault


def get_device_repository(db: Annotated[Database, Depends(get_db)]) -> DeviceRepository:
    return DeviceRepository(db)


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Database, Depends(get_db)]
VaultDep = Annotated[CredentialVault, Depends(get_vault)]
DeviceRepositoryDep = Annotated[DeviceRepository, Depends(get_device_repository)]
