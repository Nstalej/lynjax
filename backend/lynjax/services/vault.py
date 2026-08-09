"""Encrypted storage for infrastructure credentials.

Ported from NetVault's ``CredentialVault``. Behaviour kept: Fernet (AES-128-CBC
with HMAC-SHA256) over a JSON payload, one row per named credential.

Changed on purpose:

* **The key is passed in, never read from the environment.** NetVault fell back
  to ``os.getenv`` inside the class, so the vault's identity depended on ambient
  process state and tests could silently encrypt with the developer's real key.
* **A machine-generated Fernet key is used directly.** NetVault always ran
  PBKDF2 over the key with a hardcoded shared salt, which adds nothing to an
  already-random 32-byte key. Derivation now happens only when the operator
  supplies a passphrase instead.
* **Failures are typed.** Callers can distinguish "no such credential" from
  "wrong key" instead of catching bare exceptions.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from lynjax.core.database import Database

logger = logging.getLogger("lynjax.vault")

#: Fixed salt, used only when deriving a key from an operator passphrase.
#: Deterministic on purpose: the same passphrase must open the same vault after
#: the database file is copied to another machine. It is not a secret, and it is
#: not needed at all for machine-generated keys.
_PASSPHRASE_SALT = b"lynjax.vault.pbkdf2.v1"

#: OWASP's 2023 floor for PBKDF2-HMAC-SHA256.
_PBKDF2_ITERATIONS = 600_000


class VaultError(RuntimeError):
    """Base class for vault failures."""


class CredentialNotFoundError(VaultError):
    """The requested credential does not exist."""


class VaultDecryptionError(VaultError):
    """Stored data could not be decrypted, usually a changed master key."""


def _build_fernet(master_key: str) -> Fernet:
    """Return a Fernet from either a real Fernet key or an operator passphrase."""
    if not master_key:
        raise VaultError(
            "A master key is required. Set LYNJAX_CREDENTIALS_MASTER_KEY, or let "
            "`lynjax init` generate one."
        )

    try:
        return Fernet(master_key.encode("utf-8"))
    except (ValueError, TypeError):
        # Not a Fernet key, so treat the value as a passphrase and derive one.
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_PASSPHRASE_SALT,
            iterations=_PBKDF2_ITERATIONS,
        )
        derived = base64.urlsafe_b64encode(kdf.derive(master_key.encode("utf-8")))
        return Fernet(derived)


class CredentialVault:
    """Stores and retrieves credentials, encrypted at rest."""

    def __init__(self, db: Database, master_key: str) -> None:
        self._db = db
        self._fernet = _build_fernet(master_key)

    # ─── Primitives ───

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise VaultDecryptionError(
                "Cannot decrypt the stored value. The master key most likely "
                "changed; restore the original LYNJAX_CREDENTIALS_MASTER_KEY."
            ) from exc

    def _encrypt_payload(self, data: dict[str, Any]) -> str:
        return self.encrypt(json.dumps(data, sort_keys=True))

    def _decrypt_payload(self, ciphertext: str) -> dict[str, Any]:
        return json.loads(self.decrypt(ciphertext))

    # ─── Storage ───

    async def store(self, name: str, credential_type: str, data: dict[str, Any]) -> int:
        """Insert a credential, or replace the payload of one that exists.

        Returns the row id. Names are unique, so storing twice under one name
        updates rather than silently creating a shadow copy, which is what
        NetVault's bare INSERT did until the UNIQUE constraint rejected it.
        """
        encrypted = self._encrypt_payload(data)
        await self._db.execute(
            """
            INSERT INTO credential_store (name, type, encrypted_data)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                type = excluded.type,
                encrypted_data = excluded.encrypted_data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, credential_type, encrypted),
        )
        row = await self._db.fetch_one(
            "SELECT id FROM credential_store WHERE name = ?", (name,)
        )
        logger.info("Stored credential %r (type=%s)", name, credential_type)
        return int(row["id"]) if row else 0

    async def get(self, name: str) -> dict[str, Any]:
        """Return the decrypted payload, raising if the name is unknown."""
        record = await self.get_record(name)
        return record["data"]

    async def get_record(self, name: str) -> dict[str, Any]:
        """Return metadata plus the decrypted payload."""
        row = await self._db.fetch_one(
            "SELECT id, name, type, encrypted_data, created_at, updated_at "
            "FROM credential_store WHERE name = ?",
            (name,),
        )
        if row is None:
            raise CredentialNotFoundError(f"No credential named {name!r}")

        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "data": self._decrypt_payload(row["encrypted_data"]),
        }

    async def exists(self, name: str) -> bool:
        row = await self._db.fetch_one(
            "SELECT 1 FROM credential_store WHERE name = ?", (name,)
        )
        return row is not None

    async def delete(self, name: str) -> None:
        """Remove a credential. Raises if it was not there to begin with."""
        if not await self.exists(name):
            raise CredentialNotFoundError(f"No credential named {name!r}")
        await self._db.execute("DELETE FROM credential_store WHERE name = ?", (name,))
        logger.info("Deleted credential %r", name)

    async def list_metadata(self) -> list[dict[str, Any]]:
        """List stored credentials without ever decrypting them.

        Metadata only, by design: listing is a routine UI call and must not put
        plaintext secrets in memory.
        """
        return await self._db.fetch_all(
            "SELECT id, name, type, created_at, updated_at "
            "FROM credential_store ORDER BY name"
        )

    async def purge_all(self) -> int:
        """Delete every credential and return how many were removed.

        Field work needs this: after an authorised assessment the client's
        credentials must leave the laptop.
        """
        rows = await self._db.fetch_all("SELECT COUNT(*) AS n FROM credential_store")
        count = int(rows[0]["n"]) if rows else 0
        await self._db.execute("DELETE FROM credential_store")
        logger.warning("Purged %s credential(s) from the vault", count)
        return count
