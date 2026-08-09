"""User accounts.

Authentication is not optional and there is no anonymous mode, so the state
"no users exist yet" has to be handled explicitly rather than by leaving the API
open until someone gets round to creating one.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from lynjax.core.database import Database
from lynjax.core.security import (
    Role,
    hash_password,
    is_valid_email,
    normalise_email,
    verify_password,
)

logger = logging.getLogger("lynjax.users")


class UserError(RuntimeError):
    """Base class for account failures."""


class UserNotFoundError(UserError):
    """No account matches."""


class DuplicateUserError(UserError):
    """An account already exists with that email."""


class InvalidEmailError(UserError):
    """The email is not usable as an identifier."""


@dataclass(frozen=True)
class User:
    id: int
    email: str
    role: str
    is_active: bool
    full_name: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> User:
        return cls(
            id=int(row["id"]),
            email=row["email"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            full_name=row["full_name"],
        )


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def count(self) -> int:
        rows = await self._db.fetch_all("SELECT COUNT(*) AS n FROM users")
        return int(rows[0]["n"]) if rows else 0

    async def create(
        self,
        *,
        email: str,
        password: str,
        role: Role = "viewer",
        full_name: str | None = None,
    ) -> User:
        email = normalise_email(email)
        if not is_valid_email(email):
            raise InvalidEmailError(f"{email!r} is not a valid email address.")

        if await self._find_row(email) is not None:
            raise DuplicateUserError(f"An account already exists for {email}.")

        # hash_password validates the policy and raises WeakPasswordError, which
        # the caller surfaces; a weak password must never reach storage.
        await self._db.execute(
            "INSERT INTO users (email, hashed_password, role, full_name) "
            "VALUES (?, ?, ?, ?)",
            (email, hash_password(password), role, full_name),
        )
        logger.info("Created account %s with role %s", email, role)
        return await self.get_by_email(email)

    async def _find_row(self, email: str) -> dict[str, Any] | None:
        return await self._db.fetch_one(
            "SELECT * FROM users WHERE email = ?", (normalise_email(email),)
        )

    async def get_by_email(self, email: str) -> User:
        row = await self._find_row(email)
        if row is None:
            raise UserNotFoundError(f"No account for {email}.")
        return User.from_row(row)

    async def list(self) -> list[User]:
        return [
            User.from_row(row)
            for row in await self._db.fetch_all("SELECT * FROM users ORDER BY email")
        ]

    async def authenticate(self, email: str, password: str) -> User | None:
        """Return the user when the credentials match, otherwise None.

        The same None covers "no such account", "wrong password" and "account
        disabled" on purpose: distinguishing them for the caller would let
        anyone enumerate which addresses have accounts.
        """
        row = await self._find_row(email)

        if row is None:
            # Still hash something, so a missing account does not answer
            # measurably faster than a wrong password.
            verify_password(password, "$2b$12$" + "." * 53)
            return None

        if not verify_password(password, row["hashed_password"]):
            return None

        if not bool(row["is_active"]):
            logger.warning("Sign-in refused for disabled account %s", row["email"])
            return None

        return User.from_row(row)

    async def set_password(self, email: str, password: str) -> None:
        await self.get_by_email(email)
        await self._db.execute(
            "UPDATE users SET hashed_password = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE email = ?",
            (hash_password(password), normalise_email(email)),
        )
        logger.info("Password changed for %s", normalise_email(email))

    async def set_role(self, email: str, role: Role) -> None:
        await self.get_by_email(email)
        await self._db.execute(
            "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?",
            (role, normalise_email(email)),
        )

    async def set_active(self, email: str, is_active: bool) -> None:
        await self.get_by_email(email)
        await self._db.execute(
            "UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE email = ?",
            (1 if is_active else 0, normalise_email(email)),
        )

    async def delete(self, email: str) -> None:
        """Remove an account.

        Refuses to remove the last admin: an install with no administrator
        cannot be recovered through the API.
        """
        user = await self.get_by_email(email)

        if user.role == "admin":
            rows = await self._db.fetch_all(
                "SELECT COUNT(*) AS n FROM users WHERE role = 'admin' AND is_active = 1"
            )
            if int(rows[0]["n"]) <= 1:
                raise UserError(
                    "This is the only active administrator. Promote another "
                    "account before removing it, or the install cannot be "
                    "administered."
                )

        await self._db.execute(
            "DELETE FROM users WHERE email = ?", (normalise_email(email),)
        )
        logger.info("Deleted account %s", user.email)
