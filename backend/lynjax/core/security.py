"""Password hashing and access tokens.

Two dependency choices worth recording, both replacing what NetVault used:

* **bcrypt directly, not passlib.** passlib 1.7.4 reads ``bcrypt.__about__``,
  which bcrypt 4.1 removed, so the pairing NetVault pinned emits errors on any
  current install. bcrypt's own API is small enough that the wrapper earns
  nothing.
* **PyJWT, not python-jose.** python-jose has been effectively unmaintained and
  carries known advisories; PyJWT is the maintained option for the one thing
  needed here.

There is no way to turn authentication off. A switch for that is precisely what
ends up deployed on a server by accident.
"""

from __future__ import annotations

import hmac
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

logger = logging.getLogger("lynjax.security")

Role = Literal["admin", "operator", "viewer"]

#: Roles ordered by privilege, so a check is a comparison rather than a list of
#: equality tests that drifts as roles are added.
ROLE_RANK: dict[str, int] = {"viewer": 0, "operator": 1, "admin": 2}

ALGORITHM = "HS256"

#: bcrypt truncates silently at 72 bytes. Rejecting longer input is better than
#: accepting a password whose tail never mattered.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 12

#: Passwords that a scanner will try in its first hundred guesses.
OBVIOUS_PASSWORDS = frozenset(
    {
        "password",
        "password123",
        "administrator",
        "changeme",
        "lynjax",
        "lynjax123",
        "12345678",
        "123456789012",
        "qwertyuiop",
        "letmein",
    }
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SecurityError(RuntimeError):
    """Base class for authentication failures."""


class WeakPasswordError(SecurityError):
    """The password does not meet the minimum policy."""


class InvalidTokenError(SecurityError):
    """The token is missing, malformed, expired or signed with another key."""


def validate_password(password: str) -> None:
    """Raise ``WeakPasswordError`` unless the password is acceptable.

    Deliberately checked at the point a password is set, not at login: an
    existing weak password should still let its owner in so they can change it.
    """
    # Checked before length: telling someone their well-known password is
    # merely "too short" invites them to pad it to twelve characters.
    if password.lower() in OBVIOUS_PASSWORDS:
        raise WeakPasswordError(
            "That password appears in every credential-guessing list. Choose "
            "another."
        )

    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"The password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise WeakPasswordError(
            f"The password must be at most {MAX_PASSWORD_BYTES} bytes. bcrypt "
            f"silently ignores anything beyond that, so a longer one would give "
            f"false confidence."
        )


def hash_password(password: str) -> str:
    """Hash a password for storage. Validates the policy first."""
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Check a password against a stored hash, without raising on bad input."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # A malformed stored hash must read as "wrong password", never as an
        # exception that a caller might mistake for a server fault.
        return False


def create_access_token(
    *,
    subject: str,
    role: str,
    secret: str,
    expires_in: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expiry = now + (expires_in or timedelta(hours=8))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expiry,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict[str, Any]:
    """Decode and verify a token, or raise ``InvalidTokenError``.

    ``algorithms`` is pinned to one entry on purpose: accepting a list the
    caller does not control is how the "alg: none" family of bypasses works.
    """
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("The session expired. Sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("The token is not valid.") from exc


def has_privilege(role: str, minimum: Role) -> bool:
    """True when ``role`` is at least ``minimum``."""
    return ROLE_RANK.get(role, -1) >= ROLE_RANK[minimum]


def normalise_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
