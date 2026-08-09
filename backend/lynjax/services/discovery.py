"""Network discovery.

This is the most sensitive component in Lynjax. Every other part talks to a
device someone deliberately registered; this one reaches addresses nobody named.
An unauthorised scan is, in many jurisdictions, the part of this product that
gets its operator in trouble — so the guards here are deliberate, not defensive
padding:

* the network policy must already be set to ``authorized-targets``;
* the scope has a hard host cap, so a typo like ``10.0.0.0/8`` is refused
  instead of quietly launching sixteen million probes;
* public address space is refused unless the caller explicitly opts in, because
  a private range is almost always what was meant on a client site;
* credentials are never guessed. NetVault probed TCP/161 to "detect SNMP",
  which finds nothing because SNMP is UDP. Doing it properly needs a community
  string, and trying common ones would be credential brute force, so SNMP
  detection is skipped unless the operator supplies one.

Ported from NetVault's ``NetworkDiscoveryEngine``, which had none of the above
and materialised every target address in a list before starting.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import socket
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from lynjax.core.config import Settings
from lynjax.services.connector_factory import assert_network_allowed
from lynjax.services.connectors.base import utc_now
from lynjax.services.devices import DeviceRepository

logger = logging.getLogger("lynjax.discovery")

DiscoveryMethod = Literal["tcp", "ssh", "snmp"]
JobStatus = Literal["running", "completed", "failed", "cancelled"]

#: Refuse a scope larger than this many addresses. A /20 is already 4094 hosts,
#: which is a large site; anything bigger is almost certainly a mistyped mask.
DEFAULT_MAX_HOSTS = 4096

#: Ports probed for plain reachability.
REACHABILITY_PORTS = (22, 80, 443, 445, 8080)

#: SSH banner fragments that identify a vendor.
BANNER_HINTS = {
    "mikrotik": "mikrotik",
    "routeros": "mikrotik",
    "cisco": "cisco",
    "ruckus": "access-point",
    "rkscli": "access-point",
    "ubnt": "ubiquiti",
    "openssh": "generic-unix",
}


class DiscoveryError(RuntimeError):
    """Base class for discovery failures."""


class ScopeTooLargeError(DiscoveryError):
    """The requested scope exceeds the host cap."""


class PublicScopeRefusedError(DiscoveryError):
    """The scope covers public address space without an explicit opt-in."""


@dataclass(frozen=True)
class DiscoveredHost:
    ip: str
    open_ports: tuple[int, ...]
    hostname: str = ""
    device_hint: str = "unknown"
    banner: str = ""
    already_registered: bool = False


@dataclass
class DiscoveryJob:
    job_id: str
    networks: tuple[str, ...]
    methods: tuple[str, ...]
    total_hosts: int
    status: JobStatus = "running"
    scanned_hosts: int = 0
    responding_hosts: int = 0
    results: list[DiscoveredHost] = field(default_factory=list)
    error: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    @property
    def progress_percent(self) -> float:
        if not self.total_hosts:
            return 100.0
        return round(100 * self.scanned_hosts / self.total_hosts, 1)


def parse_scope(
    subnets: list[str],
    *,
    max_hosts: int = DEFAULT_MAX_HOSTS,
    allow_public: bool = False,
) -> list[ipaddress.IPv4Network]:
    """Validate a scan scope, refusing anything oversized or unexpectedly public.

    Raising here is the point: a refused scope costs the operator ten seconds,
    while an accidental scan of the wrong range can cost them the engagement.
    """
    if not subnets:
        raise DiscoveryError("At least one subnet is required.")

    networks: list[ipaddress.IPv4Network] = []
    total = 0

    for raw in subnets:
        try:
            network = ipaddress.ip_network(raw, strict=False)
        except ValueError as exc:
            raise DiscoveryError(f"{raw!r} is not a valid subnet: {exc}") from exc

        if not isinstance(network, ipaddress.IPv4Network):
            raise DiscoveryError(f"Only IPv4 scopes are supported: {raw}")

        if not allow_public and not (network.is_private or network.is_loopback):
            raise PublicScopeRefusedError(
                f"{network} is public address space. Scanning it is refused "
                f"unless you pass allow_public, and you should only do that "
                f"with written authorisation covering those addresses."
            )

        networks.append(network)
        total += max(network.num_addresses - 2, 1)

    if total > max_hosts:
        raise ScopeTooLargeError(
            f"The requested scope covers {total} addresses, over the limit of "
            f"{max_hosts}. Narrow the range, or raise max_hosts deliberately."
        )

    return networks


def iter_hosts(networks: list[ipaddress.IPv4Network]) -> Iterator[str]:
    """Yield every host address lazily.

    A generator, not a list: NetVault built the full target list up front, so a
    wide scope allocated the whole address space before probing anything.
    """
    for network in networks:
        if network.num_addresses <= 2:
            yield from (str(address) for address in network)
        else:
            yield from (str(address) for address in network.hosts())


async def is_tcp_port_open(ip: str, port: int, timeout: float) -> bool:
    writer = None
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=timeout
        )
        return True
    except (TimeoutError, OSError):
        return False
    finally:
        if writer is not None:
            writer.close()
            with contextlib.suppress(TimeoutError, OSError):
                await writer.wait_closed()


async def read_ssh_banner(ip: str, timeout: float) -> str:
    """Read the SSH identification string, which names the vendor."""
    writer = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, 22), timeout=timeout
        )
        data = await asyncio.wait_for(reader.read(256), timeout=timeout)
        return data.decode("utf-8", errors="ignore").strip()
    except (TimeoutError, OSError):
        return ""
    finally:
        if writer is not None:
            writer.close()
            with contextlib.suppress(TimeoutError, OSError):
                await writer.wait_closed()


def hint_from_banner(banner: str) -> str:
    lowered = banner.lower()
    for fragment, hint in BANNER_HINTS.items():
        if fragment in lowered:
            return hint
    return "unknown"


async def reverse_lookup(ip: str) -> str:
    def _resolve() -> str:
        try:
            return socket.gethostbyaddr(ip)[0]
        except (OSError, socket.herror):
            return ""

    return await asyncio.to_thread(_resolve)


class DiscoveryService:
    """Runs discovery jobs in the background and reports their progress."""

    def __init__(
        self,
        repo: DeviceRepository | None = None,
        *,
        max_concurrency: int = 128,
        max_jobs: int = 20,
    ) -> None:
        self._repo = repo
        self._max_concurrency = max_concurrency
        self._max_jobs = max_jobs
        self._jobs: dict[str, DiscoveryJob] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start(
        self,
        subnets: list[str],
        settings: Settings,
        *,
        methods: list[str] | None = None,
        max_hosts: int = DEFAULT_MAX_HOSTS,
        allow_public: bool = False,
        snmp_community: str | None = None,
        timeout: float = 0.5,
    ) -> str:
        """Validate the scope, then start scanning in the background."""
        assert_network_allowed(settings)

        networks = parse_scope(subnets, max_hosts=max_hosts, allow_public=allow_public)
        chosen = self._normalise_methods(methods, snmp_community)
        total = sum(max(net.num_addresses - 2, 1) for net in networks)

        job = DiscoveryJob(
            job_id=str(uuid.uuid4()),
            networks=tuple(str(net) for net in networks),
            methods=tuple(chosen),
            total_hosts=total,
        )

        async with self._lock:
            self._jobs[job.job_id] = job
            self._prune_locked()

        logger.warning(
            "Starting network discovery job=%s scope=%s hosts=%s methods=%s",
            job.job_id,
            job.networks,
            total,
            chosen,
        )
        self._tasks[job.job_id] = asyncio.create_task(
            self._run(job, networks, snmp_community, timeout)
        )
        return job.job_id

    @staticmethod
    def _normalise_methods(
        methods: list[str] | None, snmp_community: str | None
    ) -> list[str]:
        allowed = {"tcp", "ssh", "snmp"}
        chosen = [
            m.strip().lower() for m in (methods or []) if m.strip().lower() in allowed
        ]
        if not chosen:
            chosen = ["tcp", "ssh"]

        if "snmp" in chosen and not snmp_community:
            # Guessing community strings is credential brute force, not
            # discovery. Drop the method rather than try 'public'.
            logger.info("Dropping SNMP discovery: no community string supplied.")
            chosen = [m for m in chosen if m != "snmp"]

        return chosen

    async def get_job(self, job_id: str) -> DiscoveryJob | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self) -> list[DiscoveryJob]:
        async with self._lock:
            return sorted(
                self._jobs.values(), key=lambda job: job.started_at, reverse=True
            )

    async def cancel(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        async with self._lock:
            if job := self._jobs.get(job_id):
                job.status = "cancelled"
                job.completed_at = utc_now()
        return True

    async def _run(
        self,
        job: DiscoveryJob,
        networks: list[ipaddress.IPv4Network],
        snmp_community: str | None,
        timeout: float,
    ) -> None:
        try:
            registered = await self._registered_hosts()
            semaphore = asyncio.Semaphore(self._max_concurrency)

            async def scan(ip: str) -> None:
                async with semaphore:
                    found = await self._scan_host(
                        ip, job.methods, registered, snmp_community, timeout
                    )
                async with self._lock:
                    job.scanned_hosts += 1
                    if found is not None:
                        job.responding_hosts += 1
                        job.results.append(found)

            await asyncio.gather(*(scan(ip) for ip in iter_hosts(networks)))

            async with self._lock:
                job.results.sort(key=lambda host: ipaddress.ip_address(host.ip))
                job.status = "completed"
                job.completed_at = utc_now()

            logger.info(
                "Discovery job=%s finished: %s of %s hosts responded",
                job.job_id,
                job.responding_hosts,
                job.total_hosts,
            )

        except asyncio.CancelledError:
            async with self._lock:
                job.status = "cancelled"
                job.completed_at = utc_now()
            raise
        except Exception as exc:  # noqa: BLE001 - the job must record why it died
            logger.exception("Discovery job=%s failed", job.job_id)
            async with self._lock:
                job.status = "failed"
                job.error = str(exc)
                job.completed_at = utc_now()

    async def _registered_hosts(self) -> set[str]:
        if self._repo is None:
            return set()
        return {device.host for device in await self._repo.list()}

    async def _scan_host(
        self,
        ip: str,
        methods: tuple[str, ...],
        registered: set[str],
        snmp_community: str | None,
        timeout: float,
    ) -> DiscoveredHost | None:
        open_ports: set[int] = set()
        banner = ""
        hint = "unknown"

        if "tcp" in methods:
            probes = await asyncio.gather(
                *(is_tcp_port_open(ip, port, timeout) for port in REACHABILITY_PORTS)
            )
            open_ports.update(
                port
                for port, is_open in zip(REACHABILITY_PORTS, probes, strict=False)
                if is_open
            )

        if "ssh" in methods and (
            22 in open_ports or await is_tcp_port_open(ip, 22, timeout)
        ):
            open_ports.add(22)
            banner = await read_ssh_banner(ip, timeout)
            hint = hint_from_banner(banner)

        if (
            "snmp" in methods
            and snmp_community
            and await self._snmp_responds(ip, snmp_community, timeout)
        ):
            open_ports.add(161)
            hint = "snmp-capable" if hint == "unknown" else hint

        if not open_ports:
            return None

        return DiscoveredHost(
            ip=ip,
            open_ports=tuple(sorted(open_ports)),
            hostname=await reverse_lookup(ip),
            device_hint=hint,
            banner=banner[:120],
            already_registered=ip in registered,
        )

    @staticmethod
    async def _snmp_responds(ip: str, community: str, timeout: float) -> bool:
        """Ask for sysDescr over real SNMP.

        NetVault probed TCP/161 for this. SNMP is UDP, so that check found
        essentially nothing and SNMP discovery never worked.
        """
        from lynjax.services.connectors import snmp_oids
        from lynjax.services.connectors.snmp import PySnmpTransport, build_auth_data

        transport = PySnmpTransport(
            ip,
            161,
            build_auth_data({"version": "v2c", "community": community}),
            timeout=max(timeout, 0.5),
            retries=0,
        )
        try:
            return await transport.get(snmp_oids.SYS_DESCR) is not None
        except Exception:  # noqa: BLE001 - a silent host is not an error here
            return False
        finally:
            await transport.close()

    def _prune_locked(self) -> None:
        if len(self._jobs) <= self._max_jobs:
            return

        ordered = sorted(self._jobs.values(), key=lambda job: job.started_at)
        for job in ordered[: len(self._jobs) - self._max_jobs]:
            self._jobs.pop(job.job_id, None)
            task = self._tasks.pop(job.job_id, None)
            if task and not task.done():
                task.cancel()


def summarise(job: DiscoveryJob) -> dict[str, Any]:
    """Job state as a plain dictionary, for the API layer."""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "networks": list(job.networks),
        "methods": list(job.methods),
        "total_hosts": job.total_hosts,
        "scanned_hosts": job.scanned_hosts,
        "responding_hosts": job.responding_hosts,
        "progress_percent": job.progress_percent,
        "started_at": job.started_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error,
        "results": [
            {
                "ip": host.ip,
                "hostname": host.hostname,
                "open_ports": list(host.open_ports),
                "device_hint": host.device_hint,
                "banner": host.banner,
                "already_registered": host.already_registered,
            }
            for host in job.results
        ],
    }
