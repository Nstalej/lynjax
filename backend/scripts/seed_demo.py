#!/usr/bin/env python
"""Seed a Lynjax database with a small demo inventory.

Creates credentials and devices that look like a small office network, so the
API and UI have something real to render before anyone points Lynjax at actual
equipment.

Nothing here reaches the network. The devices use documentation addresses from
RFC 5737 (192.0.2.0/24), which are reserved and routed nowhere, so a probe
against this inventory fails honestly rather than touching a stranger's host.

    python scripts/seed_demo.py             # seed the default data directory
    python scripts/seed_demo.py --reset     # wipe the inventory first
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings, ensure_runtime_secrets  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.services.devices import DeviceRepository  # noqa: E402
from app.services.vault import CredentialVault  # noqa: E402

# Reserved for documentation by RFC 5737. Never a real host.
DEMO_CREDENTIALS = [
    (
        "demo-switch-ssh",
        "ssh",
        {"username": "demo-operator", "password": "demo-only-not-a-real-secret"},
    ),
    (
        "demo-switch-snmp",
        "snmp",
        {"version": "v2c", "community": "demo-community"},
    ),
]

DEMO_DEVICES = [
    {
        "name": "demo-core-switch",
        "host": "192.0.2.1",
        "connector_type": "ssh",
        "device_type": "mikrotik",
        "credential_name": "demo-switch-ssh",
        "description": "Core switch, uplink to the firewall",
    },
    {
        "name": "demo-access-switch",
        "host": "192.0.2.2",
        "connector_type": "snmp",
        "device_type": "cisco",
        "credential_name": "demo-switch-snmp",
        "description": "Access switch, workstation ports",
    },
    {
        "name": "demo-edge-firewall",
        "host": "192.0.2.254",
        "connector_type": "ssh",
        "device_type": "auto",
        "credential_name": "demo-switch-ssh",
        "description": "Edge firewall, the far end of the chain",
    },
]


async def seed(reset: bool) -> None:
    settings = ensure_runtime_secrets(Settings())
    print(f"Data directory: {settings.data_dir}")
    print(f"Database:       {settings.db_path}")

    async with Database(settings.db_path) as database:
        vault = CredentialVault(database, settings.credentials_master_key)
        repo = DeviceRepository(database)

        if reset:
            removed_devices = await repo.purge_all()
            removed_credentials = await vault.purge_all()
            print(
                f"Reset: removed {removed_devices} device(s) and "
                f"{removed_credentials} credential(s)."
            )

        for name, kind, payload in DEMO_CREDENTIALS:
            await vault.store(name, kind, payload)
            print(f"  credential  {name}")

        for device in DEMO_DEVICES:
            if await repo.exists(device["name"]):
                print(f"  device      {device['name']} (already present, skipped)")
                continue
            await repo.create(**device)
            print(f"  device      {device['name']} at {device['host']}")

    print(
        "\nDone. Start the API with:\n"
        "    uvicorn app.main:app --reload\n"
        "then open http://127.0.0.1:8000/docs\n\n"
        "Probing these devices returns 403 until you set\n"
        "    LYNJAX_NETWORK_POLICY=authorized-targets\n"
        "which you should only do for a network you are authorised to assess."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="remove existing devices and credentials before seeding",
    )
    asyncio.run(seed(parser.parse_args().reset))


if __name__ == "__main__":
    main()
