"""Lynjax configuration.

Design rules, learned from the NetVault config layer this replaces:

1. **Flat fields only.** Nested Pydantic models are not populated from top-level
   environment variables, which silently made ``DB_PATH``, ``DASHBOARD_PORT`` and
   ``LOG_LEVEL`` dead settings in NetVault. Every field here is flat and really
   reads its environment variable.
2. **Never exit on import.** Importing this module must not terminate the
   process. Invalid configuration raises ``ConfigError``, which the caller can
   catch and report.
3. **Secrets are optional at rest.** A missing key is generated on first use
   rather than being a fatal error, so ``lynjax init`` can bootstrap a working
   install without anyone hand-editing a ``.env``.
4. **Paths follow the OS.** Data and logs go where each platform expects, so the
   same package works installed on Windows, Linux and macOS.

All environment variables use the ``LYNJAX_`` prefix, e.g. ``LYNJAX_PORT=9000``.
"""

from __future__ import annotations

import os
import secrets
import stat
from functools import lru_cache
from pathlib import Path
from typing import Literal

from platformdirs import user_data_dir, user_log_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "Lynjax"
APP_SLUG = "lynjax"
APP_VERSION = "0.6.0-dev"

#: Name of the file that stores generated secrets inside the data directory.
SECRETS_FILENAME = "secrets.env"


class ConfigError(RuntimeError):
    """Raised when configuration cannot be resolved.

    Deliberately an exception and not ``sys.exit``: callers decide how to report
    the failure.
    """


def default_data_dir() -> Path:
    return Path(user_data_dir(APP_SLUG, appauthor=False))


def default_log_dir() -> Path:
    return Path(user_log_dir(APP_SLUG, appauthor=False))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LYNJAX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Identity ───
    app_name: str = APP_NAME
    version: str = APP_VERSION
    environment: Literal["development", "testing", "production"] = "development"

    # ─── Safety ───
    # Lynjax can reach real infrastructure. Real checks stay off unless the
    # operator turns them on explicitly, so an accidental run cannot touch a
    # network nobody authorised.
    network_policy: Literal["simulated-checks-only", "authorized-targets"] = (
        "simulated-checks-only"
    )

    # ─── Server ───
    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)

    # ─── Storage ───
    data_dir: Path = Field(default_factory=default_data_dir)
    db_filename: str = "lynjax.db"

    # ─── Logging ───
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_dir: Path = Field(default_factory=default_log_dir)

    # ─── Secrets ───
    # Absent by default. ``ensure_runtime_secrets`` fills them in on first run.
    secret_key: str | None = None
    credentials_master_key: str | None = None

    @field_validator("data_dir", "log_dir", mode="before")
    @classmethod
    def _expand(cls, value: object) -> object:
        """Expand ``~`` and environment variables so operator-supplied paths work."""
        if isinstance(value, str):
            return Path(os.path.expandvars(value)).expanduser()
        return value

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_filename

    @property
    def log_file(self) -> Path:
        return self.log_dir / f"{APP_SLUG}.log"

    @property
    def secrets_file(self) -> Path:
        return self.data_dir / SECRETS_FILENAME

    @property
    def simulated_only(self) -> bool:
        """True when the app must not open connections to real infrastructure."""
        return self.network_policy == "simulated-checks-only"


def _generate_key() -> str:
    return secrets.token_urlsafe(48)


def _generate_fernet_key() -> str:
    # Imported lazily: the config module stays importable without cryptography,
    # which keeps tooling that only reads settings dependency-free.
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode("utf-8")


def _restrict_permissions(path: Path) -> None:
    """Best-effort owner-only permissions.

    POSIX honours this. On Windows the real protection is the per-user data
    directory, so a failure here is not fatal.
    """
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def ensure_runtime_secrets(settings: Settings) -> Settings:
    """Return settings with secrets guaranteed present.

    Missing keys are generated once and persisted to ``secrets.env`` in the data
    directory, so restarts keep the same keys. Without this, a regenerated
    ``credentials_master_key`` would make every stored credential undecryptable.

    Values already supplied by the environment always win and are never written
    to disk.
    """
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(
            f"Cannot create the data directory {settings.data_dir}: {exc}. "
            f"Set LYNJAX_DATA_DIR to a writable location."
        ) from exc

    stored = _read_secrets_file(settings.secrets_file)
    generated: dict[str, str] = {}

    resolved_secret = settings.secret_key or stored.get("LYNJAX_SECRET_KEY")
    if not resolved_secret:
        resolved_secret = _generate_key()
        generated["LYNJAX_SECRET_KEY"] = resolved_secret

    resolved_master = settings.credentials_master_key or stored.get(
        "LYNJAX_CREDENTIALS_MASTER_KEY"
    )
    if not resolved_master:
        resolved_master = _generate_fernet_key()
        generated["LYNJAX_CREDENTIALS_MASTER_KEY"] = resolved_master

    if generated:
        _write_secrets_file(settings.secrets_file, {**stored, **generated})

    return settings.model_copy(
        update={
            "secret_key": resolved_secret,
            "credentials_master_key": resolved_master,
        }
    )


def _read_secrets_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    except OSError as exc:
        raise ConfigError(f"Cannot read the secrets file {path}: {exc}") from exc
    return values


def _write_secrets_file(path: Path, values: dict[str, str]) -> None:
    body = "\n".join(
        [
            "# Lynjax runtime secrets - generated automatically.",
            "# Keep this file private and back it up: losing",
            "# LYNJAX_CREDENTIALS_MASTER_KEY makes stored credentials unrecoverable.",
            *(f"{key}={value}" for key, value in sorted(values.items())),
            "",
        ]
    )
    try:
        path.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot write the secrets file {path}: {exc}") from exc
    _restrict_permissions(path)


@lru_cache
def get_settings() -> Settings:
    """Cached settings for dependency injection.

    Reads only. Call ``ensure_runtime_secrets`` explicitly when the process
    actually needs the keys, so importing this module never has side effects.
    """
    return Settings()
