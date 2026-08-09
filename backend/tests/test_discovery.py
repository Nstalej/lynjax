"""Tests for network discovery.

Weighted towards the guards rather than the happy path. This is the one
component that reaches addresses nobody registered, so the tests that matter
most are the ones proving it refuses to.
"""

from __future__ import annotations

import asyncio
import ipaddress

import pytest

from lynjax.core.config import Settings
from lynjax.services.connector_factory import NetworkAccessDeniedError
from lynjax.services.discovery import (
    DEFAULT_MAX_HOSTS,
    DiscoveryError,
    DiscoveryService,
    PublicScopeRefusedError,
    ScopeTooLargeError,
    hint_from_banner,
    iter_hosts,
    parse_scope,
    summarise,
)


@pytest.fixture
def open_settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path, network_policy="authorized-targets")


class TestScopeValidation:
    def test_a_private_range_is_accepted(self):
        networks = parse_scope(["192.168.1.0/24"])

        assert networks[0] == ipaddress.ip_network("192.168.1.0/24")

    def test_a_typo_that_widens_the_scope_is_refused(self):
        """10.0.0.0/8 is sixteen million probes. Almost always a mistyped mask."""
        with pytest.raises(ScopeTooLargeError, match="over the limit"):
            parse_scope(["10.0.0.0/8"])

    def test_the_cap_can_be_raised_deliberately(self):
        assert parse_scope(["10.0.0.0/16"], max_hosts=70000)

    def test_public_address_space_is_refused_by_default(self):
        """A client site is a private range; public space needs written cover."""
        with pytest.raises(PublicScopeRefusedError, match="written authorisation"):
            parse_scope(["8.8.8.0/24"])

    def test_public_space_can_be_opted_into(self):
        assert parse_scope(["8.8.8.0/24"], allow_public=True)

    def test_loopback_is_allowed_for_local_testing(self):
        assert parse_scope(["127.0.0.0/30"])

    def test_a_malformed_subnet_is_reported_clearly(self):
        with pytest.raises(DiscoveryError, match="not a valid subnet"):
            parse_scope(["not-a-subnet"])

    def test_ipv6_is_refused_rather_than_silently_ignored(self):
        with pytest.raises(DiscoveryError, match="IPv4"):
            parse_scope(["2001:db8::/64"])

    def test_an_empty_scope_is_refused(self):
        with pytest.raises(DiscoveryError, match="At least one subnet"):
            parse_scope([])

    def test_the_cap_applies_to_the_combined_scope(self):
        """Several ranges that individually fit must not add up past the cap."""
        many = [f"10.{index}.0.0/22" for index in range(8)]

        with pytest.raises(ScopeTooLargeError):
            parse_scope(many, max_hosts=DEFAULT_MAX_HOSTS)


class TestHostIteration:
    def test_hosts_are_yielded_lazily(self):
        """A generator, not a list: NetVault materialised the whole scope."""
        hosts = iter_hosts([ipaddress.ip_network("192.168.1.0/30")])

        assert not isinstance(hosts, list)
        assert list(hosts) == ["192.168.1.1", "192.168.1.2"]

    def test_a_single_address_scope_still_yields_it(self):
        hosts = list(iter_hosts([ipaddress.ip_network("192.168.1.5/32")]))

        assert hosts == ["192.168.1.5"]


class TestBannerHints:
    @pytest.mark.parametrize(
        ("banner", "expected"),
        [
            ("SSH-2.0-ROSSSH MikroTik", "mikrotik"),
            ("SSH-2.0-Cisco-1.25", "cisco"),
            ("SSH-2.0-rkscli", "access-point"),
            ("SSH-2.0-OpenSSH_9.2", "generic-unix"),
            ("SSH-2.0-Something", "unknown"),
            ("", "unknown"),
        ],
    )
    def test_vendors_are_identified_from_the_banner(self, banner, expected):
        assert hint_from_banner(banner) == expected


class TestPolicyGate:
    async def test_discovery_is_refused_under_the_default_policy(self, tmp_path):
        """The most sensitive operation must respect the same switch."""
        service = DiscoveryService()

        with pytest.raises(NetworkAccessDeniedError):
            await service.start(["192.168.1.0/30"], Settings(data_dir=tmp_path))

    async def test_an_oversized_scope_is_refused_before_anything_starts(
        self, open_settings
    ):
        service = DiscoveryService()

        with pytest.raises(ScopeTooLargeError):
            await service.start(["10.0.0.0/8"], open_settings)

        assert await service.list_jobs() == []


class TestMethodSelection:
    def test_tcp_and_ssh_are_the_default(self):
        assert DiscoveryService._normalise_methods(None, None) == ["tcp", "ssh"]

    def test_unknown_methods_are_dropped(self):
        methods = DiscoveryService._normalise_methods(["tcp", "telepathy"], None)

        assert methods == ["tcp"]

    def test_snmp_is_dropped_when_no_community_is_supplied(self):
        """Trying common community strings would be credential brute force."""
        methods = DiscoveryService._normalise_methods(["tcp", "snmp"], None)

        assert "snmp" not in methods

    def test_snmp_is_kept_when_the_operator_supplies_a_community(self):
        methods = DiscoveryService._normalise_methods(["snmp"], "s3cret")

        assert methods == ["snmp"]


class TestScanning:
    async def test_a_scan_of_an_empty_range_completes(self, open_settings):
        """198.51.100.0/30 is RFC 5737 documentation space, routed nowhere."""
        service = DiscoveryService()

        job_id = await service.start(
            ["198.51.100.0/30"], open_settings, methods=["tcp"], timeout=0.05
        )
        await asyncio.sleep(0)
        for _ in range(100):
            job = await service.get_job(job_id)
            if job.status != "running":
                break
            await asyncio.sleep(0.05)

        assert job.status == "completed"
        assert job.responding_hosts == 0
        assert job.scanned_hosts == job.total_hosts

    async def test_progress_is_reported(self, open_settings):
        service = DiscoveryService()

        job_id = await service.start(
            ["198.51.100.0/30"], open_settings, methods=["tcp"], timeout=0.05
        )
        for _ in range(100):
            job = await service.get_job(job_id)
            if job.status != "running":
                break
            await asyncio.sleep(0.05)

        assert job.progress_percent == 100.0

    async def test_an_unknown_job_returns_none(self):
        assert await DiscoveryService().get_job("no-such-job") is None

    async def test_cancelling_an_unknown_job_reports_false(self):
        assert await DiscoveryService().cancel("no-such-job") is False


class TestSummary:
    async def test_the_summary_is_json_ready(self, open_settings):
        service = DiscoveryService()
        job_id = await service.start(
            ["198.51.100.0/32"], open_settings, methods=["tcp"], timeout=0.05
        )
        for _ in range(100):
            job = await service.get_job(job_id)
            if job.status != "running":
                break
            await asyncio.sleep(0.05)

        payload = summarise(job)

        assert payload["job_id"] == job_id
        assert payload["networks"] == ["198.51.100.0/32"]
        assert isinstance(payload["results"], list)
        assert payload["started_at"]
