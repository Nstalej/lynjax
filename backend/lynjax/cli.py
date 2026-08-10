"""The ``lynjax`` command.

This is what turns a repository into a tool. NetVault could only be run by
cloning it and calling ``python -m core.main``; there was no packaging at all,
so it could not be installed on a technician's laptop.

    lynjax init      generate keys, create the database, seed nothing
    lynjax serve     run the API and the UI on one port
    lynjax audit     run a headless assessment and write a report
    lynjax purge     delete client data after a visit
    lynjax info      show where everything lives

Built on argparse rather than a CLI framework: one fewer dependency in something
whose selling point is that it installs cleanly anywhere.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from lynjax.core.config import (
    APP_VERSION,
    ConfigError,
    Settings,
    ensure_runtime_secrets,
    get_settings,
)
from lynjax.core.database import Database
from lynjax.core.logging import configure_logging
from lynjax.services.devices import DeviceRepository
from lynjax.services.users import UserRepository
from lynjax.services.vault import CredentialVault


def _print_header() -> None:
    # ASCII only: a Windows console defaults to cp1252 and renders an em dash
    # as mojibake.
    print(f"Lynjax {APP_VERSION} - network visibility, audit and traceability")


async def _open(settings: Settings) -> Database:
    configure_logging(settings)
    database = Database(settings.db_path)
    await database.connect()
    return database


# ─── Commands ───


async def cmd_init(args: argparse.Namespace) -> int:
    """Prepare a working install: keys, directories, database schema."""
    settings = ensure_runtime_secrets(get_settings())

    database = await _open(settings)
    try:
        version = await database.get_schema_version()
        accounts = await UserRepository(database).count()
    finally:
        await database.disconnect()

    _print_header()
    print()
    print(f"  Data directory : {settings.data_dir}")
    print(f"  Database       : {settings.db_path} (schema v{version})")
    print(f"  Secrets        : {settings.secrets_file}")
    print(f"  Logs           : {settings.log_dir}")
    print(f"  Network policy : {settings.network_policy}")
    print()
    print("Keys were generated on first run and are stored in the secrets file.")
    print("Back that file up: losing the master key makes stored credentials")
    print("unrecoverable.")
    print()
    if accounts == 0:
        print("No accounts yet. Create the first administrator:")
        print("    lynjax user you@example.com --admin")
    print()
    print("Next: `lynjax serve`")
    return 0


async def cmd_info(args: argparse.Namespace) -> int:
    settings = get_settings()
    # Importing the factory registers every connector.
    import lynjax.services.connector_factory  # noqa: F401
    from lynjax.services.connectors.base import available_connectors
    from lynjax.web import find_web_root

    web_root = find_web_root()

    _print_header()
    print()
    print(f"  Data directory : {settings.data_dir}")
    print(f"  Database       : {settings.db_path}")
    print(f"  Network policy : {settings.network_policy}")
    print(f"  Connectors     : {', '.join(available_connectors())}")
    print(f"  Frontend       : {web_root or 'not built'}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Run the API and UI on one port."""
    import uvicorn

    settings = ensure_runtime_secrets(get_settings())
    host = args.host or settings.host
    port = args.port or settings.port

    _print_header()
    print()
    print(f"  Listening on   : http://{host}:{port}")
    print(f"  API docs       : http://{host}:{port}/docs")
    print(f"  Database       : {settings.db_path}")
    print(f"  Network policy : {settings.network_policy}")
    if settings.simulated_only:
        print()
        print("  Real network access is OFF. Set LYNJAX_NETWORK_POLICY=")
        print("  authorized-targets to enable it, only for networks you are")
        print("  authorised to assess.")
    print()

    uvicorn.run(
        "lynjax.main:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level=settings.log_level.lower(),
    )
    return 0


async def cmd_audit(args: argparse.Namespace) -> int:
    """Collect from every registered device and write a report."""
    from lynjax.services.assessment import run_assessment, write_report

    settings = ensure_runtime_secrets(get_settings())

    if settings.simulated_only:
        print(
            "Real network access is disabled.\n"
            "Set LYNJAX_NETWORK_POLICY=authorized-targets to run a live audit, "
            "and do that only for a network you are authorised to assess.",
            file=sys.stderr,
        )
        return 2

    database = await _open(settings)
    try:
        vault = CredentialVault(database, settings.credentials_master_key)
        repo = DeviceRepository(database)

        devices = await repo.list(active_only=True)
        if not devices:
            print(
                "No active devices in the inventory. Register some first.",
                file=sys.stderr,
            )
            return 1

        print(f"Auditing {len(devices)} device(s)...")
        assessment = await run_assessment(
            repo, vault, settings, client=args.client, trace_target=args.trace
        )

        out = Path(args.out) if args.out else Path(f"{assessment.assessment_id}.md")
        written = write_report(assessment, out, locale=args.locale)

        print(f"\n{assessment.summary}")
        print(f"Report written to {written}")
        return 0
    finally:
        await database.disconnect()


async def cmd_user(args: argparse.Namespace) -> int:
    """Create an account. The only way to bootstrap the first administrator."""
    import getpass

    from lynjax.core.security import WeakPasswordError
    from lynjax.services.users import UserError

    settings = ensure_runtime_secrets(get_settings())
    database = await _open(settings)

    try:
        users = UserRepository(database)
        first = await users.count() == 0

        if first and not args.admin:
            print(
                "This install has no accounts. The first one must be an "
                "administrator: re-run with --admin.",
                file=sys.stderr,
            )
            return 2

        password = args.password
        if not password:
            # Prompted rather than passed as an argument, so it does not land in
            # the shell history or the process list.
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Confirm password: "):
                print("The passwords do not match.", file=sys.stderr)
                return 2

        try:
            user = await users.create(
                email=args.email,
                password=password,
                role="admin" if args.admin else args.role,
            )
        except (UserError, WeakPasswordError) as exc:
            print(f"Could not create the account: {exc}", file=sys.stderr)
            return 1
    finally:
        await database.disconnect()

    print(f"Created {user.email} with role {user.role}.")
    if first:
        print("Sign in at /api/v1/auth/login.")
    return 0


async def cmd_purge(args: argparse.Namespace) -> int:
    """Remove client data after a visit."""
    settings = ensure_runtime_secrets(get_settings())

    if not args.yes:
        print(
            "This deletes every stored device and credential.\n"
            "Re-run with --yes to confirm.",
            file=sys.stderr,
        )
        return 2

    database = await _open(settings)
    try:
        vault = CredentialVault(database, settings.credentials_master_key)
        repo = DeviceRepository(database)
        devices = await repo.purge_all()
        credentials = await vault.purge_all()
    finally:
        await database.disconnect()

    print(f"Removed {devices} device(s) and {credentials} credential(s).")
    print()
    print(
        "Reports held by a running `lynjax serve` live in that process's memory "
        "and cannot be reached from here. Restart it, or call POST "
        "/api/v1/purge, to clear those too."
    )
    return 0


# ─── Entry point ───


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lynjax",
        description="Network visibility, audit and traceability.",
    )
    parser.add_argument("--version", action="version", version=f"lynjax {APP_VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="prepare keys, directories and the database")
    subparsers.add_parser("info", help="show paths, policy and available connectors")

    serve = subparsers.add_parser("serve", help="run the API and UI")
    serve.add_argument("--host", help="bind address (default 127.0.0.1)")
    serve.add_argument("--port", type=int, help="port (default 8080)")
    serve.add_argument("--reload", action="store_true", help="reload on code changes")

    audit = subparsers.add_parser("audit", help="run an assessment and write a report")
    audit.add_argument(
        "--client", default="", help="client or site name for the report"
    )
    audit.add_argument("--out", help="output path (default <assessment-id>.md)")
    audit.add_argument(
        "--locale", default="es", choices=["es", "en"], help="report language"
    )
    audit.add_argument(
        "--trace", help="trace the chain to this endpoint IP as part of the audit"
    )

    purge = subparsers.add_parser("purge", help="delete stored devices and credentials")
    purge.add_argument("--yes", action="store_true", help="confirm the deletion")

    user = subparsers.add_parser("user", help="create an account")
    user.add_argument("email", help="email address, used as the login")
    user.add_argument("--admin", action="store_true", help="grant the admin role")
    user.add_argument(
        "--role",
        default="viewer",
        choices=["viewer", "operator", "admin"],
        help="role when --admin is not given",
    )
    user.add_argument(
        "--password",
        help="password; prompted for when omitted, which keeps it out of shell history",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    handlers = {
        "init": cmd_init,
        "info": cmd_info,
        "audit": cmd_audit,
        "purge": cmd_purge,
        "user": cmd_user,
    }

    try:
        if args.command == "serve":
            return cmd_serve(args)
        return asyncio.run(handlers[args.command](args))
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
