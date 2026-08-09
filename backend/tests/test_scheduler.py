"""Tests for periodic polling.

The behaviour that matters is resilience: one bad device must not end a cycle,
and one bad cycle must not end the loop. NetVault's polling task died silently
on the first unhandled error and quietly stopped updating device status.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from lynjax.core.config import Settings
from lynjax.core.database import Database
from lynjax.services.connectors.base import ConnectionTestResult
from lynjax.services.devices import DeviceRepository
from lynjax.services.scheduler import (
    PollCycle,
    PollingScheduler,
    build_scheduler,
    poll_once,
)
from lynjax.services.vault import CredentialVault

MASTER_KEY = "vLQ5wYAJc6qHhCUW3wRDGxQ0cWQFWpQxNKZbCKzE1yA="


@pytest.fixture
async def repo(tmp_path):
    database = Database(tmp_path / "sched.db")
    await database.connect()
    try:
        yield DeviceRepository(database)
    finally:
        await database.disconnect()


@pytest.fixture
async def vault(tmp_path):
    database = Database(tmp_path / "sched-vault.db")
    await database.connect()
    try:
        yield CredentialVault(database, MASTER_KEY)
    finally:
        await database.disconnect()


@pytest.fixture
def open_settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path, network_policy="authorized-targets")


class FakeConnector:
    def __init__(self, success: bool = True, raises: Exception | None = None) -> None:
        self.success = success
        self.raises = raises
        self.disconnected = False

    async def test_connection(self):
        if self.raises is not None:
            raise self.raises
        return ConnectionTestResult(success=self.success, latency_ms=5.0)

    async def disconnect(self):
        self.disconnected = True


class TestPollOnce:
    async def test_an_empty_inventory_completes(self, repo, vault, open_settings):
        cycle = await poll_once(repo, vault, open_settings)

        assert cycle.checked == 0
        assert cycle.completed_at is not None

    async def test_a_reachable_device_is_marked_online(
        self, repo, vault, open_settings, monkeypatch
    ):
        device = await repo.create(name="sw", host="10.0.0.1", connector_type="ssh")

        async def fake_build(*_args, **_kwargs):
            return FakeConnector(success=True)

        monkeypatch.setattr("lynjax.services.scheduler.build_connector", fake_build)

        cycle = await poll_once(repo, vault, open_settings)

        assert cycle.online == 1
        assert (await repo.get(device.id)).status == "online"

    async def test_an_unreachable_device_is_marked_offline(
        self, repo, vault, open_settings, monkeypatch
    ):
        device = await repo.create(name="sw", host="10.0.0.1", connector_type="ssh")

        async def fake_build(*_args, **_kwargs):
            return FakeConnector(success=False)

        monkeypatch.setattr("lynjax.services.scheduler.build_connector", fake_build)

        cycle = await poll_once(repo, vault, open_settings)

        assert cycle.offline == 1
        assert (await repo.get(device.id)).status == "offline"

    async def test_one_failing_device_does_not_stop_the_cycle(
        self, repo, vault, open_settings, monkeypatch
    ):
        """A device failing is normal on a real network."""
        await repo.create(name="good", host="10.0.0.1", connector_type="ssh")
        await repo.create(name="bad", host="10.0.0.2", connector_type="ssh")

        async def fake_build(device, *_args, **_kwargs):
            if device.name == "bad":
                raise RuntimeError("credential missing")
            return FakeConnector(success=True)

        monkeypatch.setattr("lynjax.services.scheduler.build_connector", fake_build)

        cycle = await poll_once(repo, vault, open_settings)

        assert cycle.online == 1
        assert [name for name, _ in cycle.errors] == ["bad"]

    async def test_the_connector_is_always_released(
        self, repo, vault, open_settings, monkeypatch
    ):
        await repo.create(name="sw", host="10.0.0.1", connector_type="ssh")
        connector = FakeConnector(success=True)

        async def fake_build(*_args, **_kwargs):
            return connector

        monkeypatch.setattr("lynjax.services.scheduler.build_connector", fake_build)

        await poll_once(repo, vault, open_settings)

        assert connector.disconnected is True

    async def test_inactive_devices_are_skipped(
        self, repo, vault, open_settings, monkeypatch
    ):
        device = await repo.create(name="sw", host="10.0.0.1", connector_type="ssh")
        await repo.set_active(device.id, False)

        async def fake_build(*_args, **_kwargs):
            return FakeConnector(success=True)

        monkeypatch.setattr("lynjax.services.scheduler.build_connector", fake_build)

        assert (await poll_once(repo, vault, open_settings)).checked == 0


class TestSchedulerLifecycle:
    async def test_it_starts_and_stops(self):
        async def cycle() -> PollCycle:
            return PollCycle()

        scheduler = PollingScheduler(cycle, interval_minutes=60)

        await scheduler.start()
        assert scheduler.is_running is True

        await scheduler.stop()
        assert scheduler.is_running is False

    async def test_starting_twice_is_harmless(self):
        async def cycle() -> PollCycle:
            return PollCycle()

        scheduler = PollingScheduler(cycle, interval_minutes=60)
        await scheduler.start()
        await scheduler.start()

        assert scheduler.is_running is True
        await scheduler.stop()

    async def test_stopping_when_never_started_is_safe(self):
        async def cycle() -> PollCycle:
            return PollCycle()

        await PollingScheduler(cycle).stop()

    async def test_the_interval_never_drops_below_a_minute(self):
        async def cycle() -> PollCycle:
            return PollCycle()

        scheduler = PollingScheduler(cycle, interval_minutes=0)

        assert scheduler.interval.total_seconds() == 60


class TestResilience:
    async def test_a_failing_cycle_does_not_end_the_loop(self):
        """NetVault's polling task died on the first unhandled error and stopped
        updating device status with nothing saying so."""
        calls = {"n": 0}

        async def cycle() -> PollCycle:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return PollCycle()

        scheduler = PollingScheduler(cycle, interval_minutes=1)
        # Shorten the wait so the second cycle lands inside the test.
        scheduler.interval = timedelta(seconds=0.05)

        await scheduler.start()
        await asyncio.sleep(0.3)
        running = scheduler.is_running
        await scheduler.stop()

        assert calls["n"] > 1
        assert running is True

    async def test_the_last_cycle_is_recorded(self):
        async def cycle() -> PollCycle:
            return PollCycle(checked=3, online=2, offline=1)

        scheduler = PollingScheduler(cycle, interval_minutes=1)
        scheduler.interval = timedelta(seconds=0.05)

        await scheduler.start()
        await asyncio.sleep(0.15)
        await scheduler.stop()

        assert scheduler.last_cycle.checked == 3


class TestStatus:
    async def test_status_reports_a_stopped_scheduler(self):
        async def cycle() -> PollCycle:
            return PollCycle()

        status = PollingScheduler(cycle, interval_minutes=7).status()

        assert status["running"] is False
        assert status["interval_minutes"] == 7
        assert status["last_cycle"] is None


class TestPolicy:
    async def test_a_closed_policy_skips_the_cycle_without_erroring(
        self, repo, vault, tmp_path
    ):
        """Expected while the policy is closed; nothing is broken."""
        scheduler = build_scheduler(repo, vault, Settings(data_dir=tmp_path))
        scheduler.interval = timedelta(seconds=0.05)

        await scheduler.start()
        await asyncio.sleep(0.15)
        await scheduler.stop()

        assert scheduler.last_cycle is not None
        assert scheduler.last_cycle.checked == 0
