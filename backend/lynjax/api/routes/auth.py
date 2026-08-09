"""Sign-in and account management.

Roles, least privilege first:

* **viewer** reads the inventory and past results.
* **operator** can also probe, discover, audit and trace — everything that
  touches the client's network.
* **admin** can also manage accounts.

The split is not decorative. Reaching a client's infrastructure is the action
worth restricting, so it sits above read access and below account control.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from lynjax.core.deps import AdminDep, CurrentUserDep, SettingsDep, UserRepositoryDep
from lynjax.core.security import (
    Role,
    SecurityError,
    WeakPasswordError,
    create_access_token,
)
from lynjax.services.users import (
    DuplicateUserError,
    InvalidEmailError,
    User,
    UserError,
    UserNotFoundError,
)

logger = logging.getLogger("lynjax.api.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    full_name: str | None


class CreateUserRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=12)
    role: Role = "viewer"
    full_name: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        full_name=user.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, users: UserRepositoryDep, settings: SettingsDep
) -> TokenResponse:
    """Exchange credentials for a token."""
    if await users.count() == 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This install has no accounts yet. Create the first administrator "
            "with `lynjax user create --admin`.",
        )

    user = await users.authenticate(payload.email, payload.password)
    if user is None:
        # One message for every failure mode. Telling the caller which part was
        # wrong lets anyone enumerate accounts.
        logger.warning("Failed sign-in for %r", payload.email)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=user.email,
        role=user.role,
        secret=settings.secret_key or "",
        expires_in=None,
    )
    logger.info("Signed in: %s (%s)", user.email, user.role)
    return TokenResponse(access_token=token, email=user.email, role=user.role)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUserDep) -> UserResponse:
    return _to_response(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUserDep,
    users: UserRepositoryDep,
) -> Response:
    """Change your own password, proving you know the current one."""
    if await users.authenticate(current_user.email, payload.current_password) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The current password is wrong.")

    try:
        await users.set_password(current_user.email, payload.new_password)
    except WeakPasswordError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users", response_model=list[UserResponse])
async def list_users(_admin: AdminDep, users: UserRepositoryDep) -> list[UserResponse]:
    return [_to_response(user) for user in await users.list()]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest, _admin: AdminDep, users: UserRepositoryDep
) -> UserResponse:
    try:
        user = await users.create(
            email=payload.email,
            password=payload.password,
            role=payload.role,
            full_name=payload.full_name,
        )
    except DuplicateUserError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except (InvalidEmailError, WeakPasswordError, SecurityError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return _to_response(user)


@router.delete(
    "/users/{email}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_user(
    email: str, admin: AdminDep, users: UserRepositoryDep
) -> Response:
    if email.strip().lower() == admin.email:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You cannot delete the account you are signed in with.",
        )

    try:
        await users.delete(email)
    except UserNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except UserError as exc:
        # Covers the last-administrator guard.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
