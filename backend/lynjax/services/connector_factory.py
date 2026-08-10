"""Builds connectors for devices, and enforces the network-access policy.

This is the only place in Lynjax that turns a stored device record into
something that can open a socket, which makes it the right place to enforce
whether reaching real infrastructure is allowed at all.

That gate matters. Lynjax is used on client networks, and the difference
between "assess the range we were authorised for" and "touch equipment nobody
approved" has to be a deliberate, auditable switch rather than a default.
``LYNJAX_NETWORK_POLICY`` starts at ``simulated-checks-only`` and must be set to
``authorized-targets`` before any connector can be built.
"""

from __future__ import annotations

import logging

from lynjax.core.config import Settings

# Imported for their side effect: each module registers itself in the connector
# registry at import time, so this is where the available set is decided.
from lynjax.services.connectors import rest as _rest  # noqa: F401
from lynjax.services.connectors import snmp as _snmp  # noqa: F401
from lynjax.services.connectors import ssh as _ssh  # noqa: F401
from lynjax.services.connectors.base import BaseConnector, get_connector
from lynjax.services.devices import Device
from lynjax.services.vault import CredentialNotFoundError, CredentialVault

logger = logging.getLogger("lynjax.connector_factory")


class NetworkAccessDeniedError(RuntimeError):
    """Raised when real network access is attempted under a simulated-only policy."""


class ConnectorNotAvailableError(RuntimeError):
    """The device names a connector type that is not registered."""


class MissingCredentialError(RuntimeError):
    """The device has no usable credential."""


def assert_network_allowed(settings: Settings) -> None:
    """Raise unless the operator has explicitly enabled real network access."""
    if settings.simulated_only:
        raise NetworkAccessDeniedError(
            "Real network access is disabled. Lynjax runs with "
            "LYNJAX_NETWORK_POLICY=simulated-checks-only by default. Set it to "
            "'authorized-targets' only for a network you have written "
            "authorisation to assess."
        )


async def build_connector(
    device: Device,
    vault: CredentialVault,
    settings: Settings,
) -> BaseConnector:
    """Return a ready connector for ``device``.

    Resolves the device's credential from the vault and merges in the host and
    port from the device record, so a credential can be shared across devices
    without carrying any one device's address.
    """
    assert_network_allowed(settings)

    connector_cls = get_connector(device.connector_type)
    if connector_cls is None:
        raise ConnectorNotAvailableError(
            f"Device {device.name!r} asks for connector type "
            f"{device.connector_type!r}, which is not registered."
        )

    credentials: dict = {}
    if device.credential_name:
        try:
            credentials = dict(await vault.get(device.credential_name))
        except CredentialNotFoundError as exc:
            raise MissingCredentialError(
                f"Device {device.name!r} references credential "
                f"{device.credential_name!r}, which is not in the vault."
            ) from exc
    elif device.connector_type != "snmp":
        # SNMP v2c can work from a community string alone, which may be carried
        # in the credential; every other connector needs one.
        raise MissingCredentialError(
            f"Device {device.name!r} has no credential attached."
        )

    credentials.setdefault("port", device.effective_port)
    if device.device_type and device.device_type != "auto":
        credentials.setdefault("device_type", device.device_type)

    logger.info(
        "Built %s connector for %r at %s",
        device.connector_type,
        device.name,
        device.host,
    )
    return connector_cls(str(device.id), device.host, credentials)
