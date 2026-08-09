"""FastAPI dependencies.

Everything the routes need is resolved through these, so tests can override any
one of them without touching application state or the filesystem.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lynjax.core.config import Settings, get_settings
from lynjax.core.database import Database
from lynjax.core.security import (
    InvalidTokenError,
    Role,
    decode_access_token,
    has_privilege,
)
from lynjax.services.devices import DeviceRepository
from lynjax.services.users import User, UserNotFoundError, UserRepository
from lynjax.services.vault import CredentialVault

# auto_error=False so a missing header produces our own message rather than
# FastAPI's generic one, which does not say what to do about it.
_bearer = HTTPBearer(auto_error=False)


def get_runtime_settings(request: Request) -> Settings:
    """The settings the process is actually running with.

    `get_settings()` returns the raw cached instance, whose secret fields are
    still None; `ensure_runtime_secrets` resolves them into a *copy* that the
    lifespan stores on app.state. Serving the raw one signed tokens with an
    empty key, which surfaced as a 500 on login inside the container while the
    tests passed, because their fixtures inject a secret explicitly.
    """
    resolved = getattr(request.app.state, "settings", None)
    return resolved if resolved is not None else get_settings()


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_vault(request: Request) -> CredentialVault:
    return request.app.state.vault


def get_device_repository(db: Annotated[Database, Depends(get_db)]) -> DeviceRepository:
    return DeviceRepository(db)


def get_user_repository(db: Annotated[Database, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> User:
    """Resolve the signed-in user, or refuse.

    The user is re-read from the database on every request rather than trusted
    from the token. A token stays valid until it expires, so a disabled account
    or a demoted role has to take effect now, not in eight hours.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required. Sign in at /api/v1/auth/login and send the "
            "token as `Authorization: Bearer <token>`.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(
            credentials.credentials, settings.secret_key or ""
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = payload.get("sub")
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token.")

    try:
        user = await users.get_by_email(email)
    except UserNotFoundError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "The account no longer exists."
        ) from exc

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")

    return user


def require_role(minimum: Role):
    """Dependency factory refusing anyone below ``minimum``."""

    async def guard(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not has_privilege(current_user.role, minimum):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action needs the {minimum} role; your account is "
                f"{current_user.role}.",
            )
        return current_user

    return guard


SettingsDep = Annotated[Settings, Depends(get_runtime_settings)]
DatabaseDep = Annotated[Database, Depends(get_db)]
VaultDep = Annotated[CredentialVault, Depends(get_vault)]
DeviceRepositoryDep = Annotated[DeviceRepository, Depends(get_device_repository)]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]

CurrentUserDep = Annotated[User, Depends(get_current_user)]
ViewerDep = Annotated[User, Depends(require_role("viewer"))]
#: Anything that reaches the client's network needs at least this.
OperatorDep = Annotated[User, Depends(require_role("operator"))]
AdminDep = Annotated[User, Depends(require_role("admin"))]
