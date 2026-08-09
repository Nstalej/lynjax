"""Periodic polling of registered devices.

Ported from NetVault's scheduler, minus APScheduler. The whole job is "run this
coroutine every N minutes and do not let one failure kill the loop", which
asyncio does directly; a scheduling framework would be a dependency carried for
a feature nobody asked for.

Off by default. A field audit runs on demand, and a tool that starts touching a
client's network on a timer the moment it launches is not what anyone wants on a
laptop. Continuous polling is for the server deployment, and it is opt-in.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from lynjax.core.config import Settings
from lynjax.services.connector_factory import (
    NetworkAccessDeniedError,
    build_connector,
)
from lynjax.services.connectors.base import ConnectorError, utc_now
from lynjax.services.devices import DeviceRepository
from lynjax.services.vault import CredentialVault

logger = logging.getLogger("lynjax.scheduler")


@dataclass
class PollCycle:
    """What one pass over the inventory did."""

    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    checked: int = 0
    online: int = 0
    offline: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()


async def poll_once(
    repo: DeviceRepository,
    vault: CredentialVault,
    settings: Settings,
    *,
    concurrency: int = 10,
) -> PollCycle:
    """Probe every active device once and record each result.

    One device failing is normal on a real network, so failures are collected
    rather than raised; the cycle finishes and reports what went wrong.
    """
    cycle = PollCycle()
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def probe(device) -> None:
        async with semaphore:
            try:
                connector = await build_connector(device, vault, settings)
            except Exception as exc:  # noqa: BLE001 - one device must not stop the cycle
                cycle.errors.append((device.name, str(exc)))
                return

            try:
                result = await connector.test_connection()
            except ConnectorError as exc:
                cycle.errors.append((device.name, str(exc)))
                result = None
            finally:
                await connector.disconnect()

            cycle.checked += 1
            reachable = bool(result and result.success)
            if reachable:
                cycle.online += 1
            else:
                cycle.offline += 1

            await repo.update_status(
                device.id, "online" if reachable else "offline", seen=reachable
            )

    devices = await repo.list(active_only=True)
    await asyncio.gather(*(probe(device) for device in devices))

    cycle.completed_at = utc_now()
    logger.info(
        "Poll cycle finished in %.1fs: %s online, %s offline, %s error(s)",
        cycle.duration_seconds,
        cycle.online,
        cycle.offline,
        len(cycle.errors),
    )
    return cycle


class PollingScheduler:
    """Runs a coroutine on an interval until stopped."""

    def __init__(
        self,
        task: Callable[[], Awaitable[PollCycle]],
        *,
        interval_minutes: int = 5,
    ) -> None:
        self._task = task
        self.interval = timedelta(minutes=max(1, interval_minutes))
        self._loop_task: asyncio.Task | None = None
        self.last_cycle: PollCycle | None = None
        self.next_run: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._loop_task is not None and not self._loop_task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        self._loop_task = asyncio.create_task(self._run())
        logger.info(
            "Polling started, every %s minute(s)",
            int(self.interval.total_seconds() // 60),
        )

    async def stop(self) -> None:
        if self._loop_task is None:
            return

        self._loop_task.cancel()
        try:
            await self._loop_task
        except asyncio.CancelledError:
            pass
        finally:
            self._loop_task = None
            self.next_run = None
        logger.info("Polling stopped")

    async def _run(self) -> None:
        while True:
            try:
                self.last_cycle = await self._task()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                # A crashed cycle must not end the loop. NetVault's polling task
                # died silently on the first unhandled error and stopped
                # updating device status without anything saying so.
                logger.exception("Poll cycle failed; the loop continues")

            self.next_run = utc_now() + self.interval
            await asyncio.sleep(self.interval.total_seconds())

    def status(self) -> dict:
        return {
            "running": self.is_running,
            "interval_minutes": int(self.interval.total_seconds() // 60),
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_cycle": (
                {
                    "started_at": self.last_cycle.started_at.isoformat(),
                    "duration_seconds": round(self.last_cycle.duration_seconds, 2),
                    "checked": self.last_cycle.checked,
                    "online": self.last_cycle.online,
                    "offline": self.last_cycle.offline,
                    "errors": [
                        {"device": name, "reason": reason}
                        for name, reason in self.last_cycle.errors
                    ],
                }
                if self.last_cycle
                else None
            ),
        }


def build_scheduler(
    repo: DeviceRepository,
    vault: CredentialVault,
    settings: Settings,
    *,
    interval_minutes: int = 5,
    concurrency: int = 10,
) -> PollingScheduler:
    """A scheduler that polls the inventory on an interval."""

    async def cycle() -> PollCycle:
        try:
            return await poll_once(repo, vault, settings, concurrency=concurrency)
        except NetworkAccessDeniedError:
            # Expected while the policy is still closed. Logged at info, not as
            # an error: nothing is broken.
            logger.info("Skipping poll cycle: real network access is disabled")
            return PollCycle(completed_at=utc_now())

    return PollingScheduler(cycle, interval_minutes=interval_minutes)
