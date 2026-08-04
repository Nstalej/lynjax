"""SSH connector for RouterOS and Cisco IOS devices.

Ported from NetVault's ``ssh_connector``. The interactive-shell path is kept
because a real MikroTik CRS354 needed it: RouterOS refuses ``exec_command`` in
some configurations and only answers over an interactive channel.

Changes made during the port:

* **The SSH client is injected.** NetVault called ``paramiko.SSHClient()``
  inline, which made the connector impossible to test without hardware, so it
  had no tests at all. A ``client_factory`` argument lets the suite drive it
  with a fake transport.
* **Failures are typed.** ``connect`` used to swallow every exception and
  return ``False``, collapsing "wrong password" and "host unreachable" into one
  useless signal. Auth failures now raise ``ConnectorAuthError`` and everything
  else ``ConnectorUnreachableError``.
* **``test_connection`` no longer closes a session it did not open.** The old
  ``finally`` block disconnected unconditionally, so probing a live connector
  silently killed it.
* **Device detection no longer keys on the substring ``exec``**, which appears
  in plenty of unrelated banner text and misidentified devices as Cisco.

Host key policy stays as NetVault had it, which was right: reject unknown keys
unless the operator explicitly opts in.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

import paramiko
from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError

from app.services.connectors.base import (
    ArpEntry,
    AuditCheck,
    AuditResult,
    BaseConnector,
    ConnectionTestResult,
    ConnectorAuthError,
    ConnectorError,
    ConnectorUnreachableError,
    InterfaceInfo,
    MacEntry,
    RouteEntry,
    register_connector,
)
from app.services.connectors.parsers import cisco, mikrotik

logger = logging.getLogger("lynjax.connectors.ssh")

DeviceType = str

#: Commands per device family. Keeping them in one table makes it obvious what
#: the connector actually runs on someone's equipment.
COMMANDS: dict[str, dict[str, str]] = {
    "mikrotik": {
        "system": "/system resource print",
        "interfaces": "/interface print",
        "arp": "/ip arp print",
        "routes": "/ip route print",
    },
    "cisco": {
        "system": "show version",
        "interfaces": "show ip interface brief",
        "arp": "show ip arp",
        "mac": "show mac address-table",
        "routes": "show ip route",
    },
}


class SSHConnector(BaseConnector):
    """Collects device state over SSH."""

    def __init__(
        self,
        device_id: str,
        device_ip: str,
        credentials: dict[str, Any],
        *,
        client_factory: Callable[[], Any] = paramiko.SSHClient,
    ) -> None:
        super().__init__(device_id, device_ip, credentials)

        self.port = int(credentials.get("port", 22))
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.key_filename = credentials.get("key_filename")
        self.timeout = float(credentials.get("timeout", 10))
        self.device_type: DeviceType = credentials.get("device_type", "auto")

        mode = str(credentials.get("ssh_mode", "exec")).strip().lower()
        self.ssh_mode = mode if mode in {"exec", "interactive"} else "exec"

        self.shell_prompt = credentials.get("shell_prompt", "#")
        self.known_hosts_file = credentials.get("known_hosts_file")
        self.allow_unknown_host_keys = bool(
            credentials.get("allow_unknown_host_keys", False)
        )

        self._client_factory = client_factory
        self._client: Any | None = None
        self._shell: Any | None = None

    # ─── Host keys ───

    def _configure_host_keys(self, client: Any) -> None:
        client.load_system_host_keys()

        if self.known_hosts_file:
            try:
                client.load_host_keys(self.known_hosts_file)
            except OSError as exc:
                logger.warning(
                    "Could not load known_hosts %s: %s", self.known_hosts_file, exc
                )

        if self.allow_unknown_host_keys:
            logger.warning(
                "Accepting unknown host keys for %s. This disables "
                "man-in-the-middle protection.",
                self.device_ip,
            )
            client.set_missing_host_key_policy(paramiko.WarningPolicy())
        else:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())

    def _connect_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "hostname": self.device_ip,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
            "look_for_keys": True,
            "allow_agent": True,
        }
        if self.password:
            kwargs["password"] = self.password
        if self.key_filename:
            kwargs["key_filename"] = self.key_filename
        return kwargs

    # ─── Lifecycle ───

    async def connect(self) -> bool:
        """Open the session.

        Raises ``ConnectorAuthError`` when credentials are rejected and
        ``ConnectorUnreachableError`` for anything else, so the caller can tell
        a wrong password from an unplugged switch.
        """
        if self._is_connected:
            return True

        client = self._client_factory()
        self._configure_host_keys(client)
        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(
                None, lambda: client.connect(**self._connect_kwargs())
            )
        except AuthenticationException as exc:
            raise ConnectorAuthError(
                f"{self.device_ip} rejected the supplied credentials"
            ) from exc
        except (NoValidConnectionsError, OSError, TimeoutError) as exc:
            raise ConnectorUnreachableError(
                f"Cannot reach {self.device_ip}:{self.port}: {exc}"
            ) from exc

        self._client = client
        self._is_connected = True

        if self.ssh_mode == "interactive":
            await loop.run_in_executor(None, self._open_interactive_shell)

        if self.device_type == "auto":
            await self._detect_device_type()

        logger.info(
            "Connected to %s as %s (%s mode)",
            self.device_ip,
            self.device_type,
            self.ssh_mode,
        )
        return True

    async def disconnect(self) -> None:
        if self._shell is not None:
            try:
                self._shell.close()
            except Exception as exc:  # noqa: BLE001 - closing must never raise
                logger.warning("Error closing shell for %s: %s", self.device_ip, exc)
            self._shell = None

        if self._client is not None:
            try:
                self._client.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error closing client for %s: %s", self.device_ip, exc)
            self._client = None

        self._is_connected = False

    async def test_connection(self) -> ConnectionTestResult:
        """Probe reachability and credentials.

        Leaves an already-open session alone. NetVault disconnected in a
        ``finally`` regardless of who opened the connection.
        """
        was_connected = self._is_connected
        start = time.perf_counter()

        try:
            await self.connect()
            latency_ms = (time.perf_counter() - start) * 1000
            return ConnectionTestResult(success=True, latency_ms=latency_ms)
        except ConnectorError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            return ConnectionTestResult(
                success=False, latency_ms=latency_ms, error_message=str(exc)
            )
        finally:
            if not was_connected and self._is_connected:
                await self.disconnect()

    # ─── Interactive shell ───

    def _open_interactive_shell(self) -> None:
        if self._client is None:
            raise ConnectorError("SSH client is not initialised")
        if not self.username or not self.password:
            raise ConnectorAuthError(
                "Interactive mode needs both a username and a password"
            )

        shell = self._client.invoke_shell()
        shell.settimeout(self.timeout)
        self._interactive_login(shell)
        self._shell = shell

    def _read_until(self, channel: Any, patterns: list[str], timeout: float) -> str:
        deadline = time.monotonic() + timeout
        buffer = ""
        wanted = [pattern.lower() for pattern in patterns if pattern]

        while time.monotonic() < deadline:
            if not channel.recv_ready():
                time.sleep(0.05)
                continue

            data = channel.recv(4096)
            if not data:
                break
            buffer += data.decode("utf-8", errors="ignore")

            lowered = buffer.lower()
            if any(pattern in lowered for pattern in wanted):
                return buffer

        raise TimeoutError(f"Timed out waiting for any of: {patterns}")

    def _interactive_login(self, channel: Any) -> None:
        banner = self._read_until(
            channel,
            ["login:", "username:", "password", self.shell_prompt],
            self.timeout,
        ).lower()

        if any(marker in banner for marker in ("login:", "username:")):
            channel.send(f"{self.username}\n".encode())
            banner = self._read_until(
                channel, ["password", self.shell_prompt], self.timeout
            ).lower()

        if "password" in banner and self.shell_prompt.lower() not in banner:
            channel.send(f"{self.password}\n".encode())
            self._read_until(channel, [self.shell_prompt], self.timeout)

    @staticmethod
    def clean_interactive_output(raw: str, command: str, prompt: str) -> str:
        """Strip the echoed command, prompts and login noise from shell output."""
        prompt_lower = prompt.lower()
        command_lower = command.strip().lower()
        cleaned: list[str] = []

        for line in raw.replace("\r", "").split("\n"):
            stripped = line.strip()
            lowered = stripped.lower()

            if not stripped or lowered == command_lower:
                continue
            if prompt_lower and prompt_lower in lowered:
                continue
            if lowered.startswith(("login:", "please login:", "password")):
                continue

            cleaned.append(stripped)

        return "\n".join(cleaned).strip()

    def _run_interactive(self, command: str) -> str:
        if self._shell is None:
            raise ConnectorError("Interactive shell is not open")

        self._shell.send(f"{command}\n".encode())
        raw = self._read_until(self._shell, [self.shell_prompt], self.timeout)
        return self.clean_interactive_output(raw, command, self.shell_prompt)

    # ─── Command execution ───

    async def execute(self, command: str) -> str:
        """Run a command and return stdout as text."""
        if not self._is_connected:
            await self.connect()

        loop = asyncio.get_running_loop()

        if self.ssh_mode == "interactive":
            return await loop.run_in_executor(None, self._run_interactive, command)

        client = self._client
        if client is None:
            raise ConnectorError("SSH client is not initialised")

        def _exec() -> str:
            _stdin, stdout, _stderr = client.exec_command(command, timeout=self.timeout)
            return stdout.read().decode("utf-8", errors="ignore")

        return await loop.run_in_executor(None, _exec)

    async def _detect_device_type(self) -> None:
        """Identify the device family from its banner.

        Only unambiguous vendor strings are trusted. NetVault also accepted the
        substring ``exec``, which appears in unrelated help text and mislabelled
        devices as Cisco.
        """
        try:
            output = await self.execute("/system resource print")
            if "RouterOS" in output or "MikroTik" in output or "board-name" in output:
                self.device_type = "mikrotik"
                return
        except ConnectorError:
            pass

        try:
            output = await self.execute("show version")
            if "Cisco" in output or "IOS" in output:
                self.device_type = "cisco"
                return
        except ConnectorError:
            pass

        self.device_type = "unknown"
        logger.warning("Could not identify the device family at %s", self.device_ip)

    async def _run_family_command(self, key: str) -> str | None:
        """Execute the command for this device family, or None when undefined."""
        command = COMMANDS.get(self.device_type, {}).get(key)
        if command is None:
            return None
        return await self.execute(command)

    # ─── Collection ───

    async def get_system_info(self) -> dict[str, Any]:
        output = await self._run_family_command("system")
        if output is None:
            return {"error": f"Unsupported device type: {self.device_type}"}

        if self.device_type == "mikrotik":
            return mikrotik.parse_system_resource(output)
        return cisco.parse_show_version(output)

    async def get_interfaces(self) -> list[InterfaceInfo]:
        output = await self._run_family_command("interfaces")
        if output is None:
            return []

        if self.device_type == "mikrotik":
            return mikrotik.parse_interfaces(output)
        return cisco.parse_show_interfaces(output)

    async def get_arp_table(self) -> list[ArpEntry]:
        output = await self._run_family_command("arp")
        if output is None:
            return []

        if self.device_type == "mikrotik":
            return mikrotik.parse_arp_table(output)
        return cisco.parse_show_ip_arp(output)

    async def get_mac_table(self) -> list[MacEntry]:
        output = await self._run_family_command("mac")
        if output is None:
            return []
        return cisco.parse_show_mac_address_table(output)

    async def get_routes(self) -> list[RouteEntry]:
        output = await self._run_family_command("routes")
        if output is None:
            return []

        if self.device_type == "mikrotik":
            return mikrotik.parse_routes(output)
        return cisco.parse_show_ip_route(output)

    # ─── Audit ───

    async def run_audit(self) -> AuditResult:
        """Collect state and report what it says about the device.

        Read-only. Every check here describes something observed; none of them
        change device configuration.
        """
        result = AuditResult(device_name=self.device_ip)

        if self.device_type == "unknown":
            result.checks.append(
                AuditCheck(
                    name="Device identification",
                    status="warning",
                    message=(
                        "Device family could not be identified, so no vendor "
                        "checks ran. Set device_type explicitly."
                    ),
                )
            )
            result.summary = "Device family unknown; audit incomplete."
            return result

        info = await self.get_system_info()
        result.checks.append(
            AuditCheck(
                name="System information",
                status="pass",
                message=f"{info.get('model', 'Unknown')} running {info.get('os_version', 'Unknown')}",
                details=info,
            )
        )

        interfaces = await self.get_interfaces()
        down = [interface for interface in interfaces if interface.status != "up"]

        if not interfaces:
            result.checks.append(
                AuditCheck(
                    name="Interfaces",
                    status="warning",
                    message="No interfaces were reported by the device.",
                )
            )
        else:
            result.checks.append(
                AuditCheck(
                    name="Interfaces",
                    status="warning" if down else "pass",
                    message=(
                        f"{len(interfaces) - len(down)} of {len(interfaces)} "
                        f"interfaces are up."
                    ),
                    details={
                        "total": len(interfaces),
                        "down": [interface.name for interface in down],
                    },
                )
            )

        arp_entries = await self.get_arp_table()
        result.checks.append(
            AuditCheck(
                name="ARP table",
                status="pass",
                message=f"{len(arp_entries)} ARP entries collected.",
                details={"entries": len(arp_entries)},
            )
        )

        result.summary = (
            f"{len(result.checks)} checks run against {self.device_ip} "
            f"({self.device_type})."
        )
        return result


register_connector("ssh", SSHConnector)
