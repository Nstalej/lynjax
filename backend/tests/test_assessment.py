"""Tests for assessment orchestration and the report.

The report is the deliverable, so these lean on it telling the truth: a device
that answered nothing must never read as healthy, and what was not covered has
to appear in writing.
"""

from __future__ import annotations

from lynjax.services.assessment import (
    Assessment,
    render_markdown,
    write_report,
)
from lynjax.services.audit import DeviceSnapshot, NetworkSnapshot, trace_chain
from lynjax.services.connectors.base import ArpEntry, AuditCheck, InterfaceInfo
from lynjax.services.devices import Device


def device(name: str, host: str, device_id: int = 1) -> Device:
    return Device(id=device_id, name=name, host=host, connector_type="ssh")


def collected(name: str = "core-sw", host: str = "10.0.0.1") -> DeviceSnapshot:
    return DeviceSnapshot(
        device=device(name, host),
        system_info={"model": "CRS354", "os_version": "7.19"},
        interfaces=[InterfaceInfo(name="ether1", status="up")],
    )


def silent(name: str = "quiet-sw", host: str = "10.0.0.2") -> DeviceSnapshot:
    """What a silent SNMP agent actually produces: a dict of blanks."""
    return DeviceSnapshot(
        device=device(name, host, 2),
        system_info={
            "name": "",
            "descr": "",
            "uptime": "",
            "location": "",
            "contact": "",
            "vendor": "generic",
        },
    )


class TestEmptinessDetection:
    def test_a_device_that_returned_data_is_not_empty(self):
        assert collected().is_empty is False

    def test_a_silent_snmp_agent_counts_as_empty(self):
        """It returns a dict of blank strings, which is not data."""
        assert silent().is_empty is True

    def test_a_device_with_only_interfaces_is_not_empty(self):
        snapshot = DeviceSnapshot(
            device=device("sw", "10.0.0.3"),
            interfaces=[InterfaceInfo(name="ether1", status="up")],
        )

        assert snapshot.is_empty is False

    def test_a_device_with_only_arp_is_not_empty(self):
        snapshot = DeviceSnapshot(
            device=device("r", "10.0.0.4"),
            arp=[
                ArpEntry(
                    ip="10.0.0.9", mac="AA:BB:CC:DD:EE:FF", interface="", type="dynamic"
                )
            ],
        )

        assert snapshot.is_empty is False

    def test_placeholder_values_do_not_count_as_data(self):
        snapshot = DeviceSnapshot(
            device=device("sw", "10.0.0.5"),
            system_info={"model": "Generic", "os_version": "Unknown"},
        )

        assert snapshot.is_empty is True


class TestSummary:
    def test_silent_devices_are_counted_separately_from_collected_ones(self):
        assessment = Assessment(
            assessment_id="a1",
            snapshot=NetworkSnapshot(devices=[collected(), silent()]),
        )

        assert "1 returned data, 1 did not respond" in assessment.summarise("en")

    def test_the_summary_is_localised(self):
        assessment = Assessment(
            assessment_id="a1", snapshot=NetworkSnapshot(devices=[collected()])
        )

        assert "dispositivo(s) evaluado(s)" in assessment.summarise("es")

    def test_findings_are_counted_by_severity(self):
        assessment = Assessment(
            assessment_id="a1",
            findings=[
                AuditCheck(name="a", status="fail", message=""),
                AuditCheck(name="b", status="warning", message=""),
            ],
        )

        summary = assessment.summarise("en")

        assert "1 critical finding(s)" in summary
        assert "1 warning(s)" in summary


class TestVerdict:
    def test_a_clean_assessment_passes(self):
        assert Assessment(assessment_id="a1").verdict == "pass"

    def test_a_critical_finding_makes_it_fail(self):
        assessment = Assessment(
            assessment_id="a1",
            findings=[AuditCheck(name="a", status="fail", message="")],
        )

        assert assessment.verdict == "fail"

    def test_a_failing_chain_trace_carries_into_the_verdict(self):
        snapshot = NetworkSnapshot(devices=[collected()])
        assessment = Assessment(
            assessment_id="a1",
            snapshot=snapshot,
            trace=trace_chain(snapshot, "10.0.0.99"),
        )

        assert assessment.verdict == "warning"


class TestReport:
    def test_a_silent_device_is_not_reported_as_ok(self):
        """The whole point: silence must never read as a healthy device."""
        assessment = Assessment(
            assessment_id="a1", snapshot=NetworkSnapshot(devices=[silent()])
        )

        report = render_markdown(assessment, "es")

        assert "Sin datos" in report
        assert "| quiet-sw | 10.0.0.2 |  | OK |" not in report

    def test_an_unreachable_device_is_listed_under_what_was_not_covered(self):
        assessment = Assessment(
            assessment_id="a1",
            unreachable=[("core-sw", "Cannot reach 10.0.0.1:22: timed out")],
        )

        report = render_markdown(assessment, "es")

        assert "Alcance no cubierto" in report
        assert "timed out" in report

    def test_findings_are_ordered_most_severe_first(self):
        assessment = Assessment(
            assessment_id="a1",
            findings=[
                AuditCheck(name="Minor", status="warning", message="m"),
                AuditCheck(name="Major", status="fail", message="M"),
            ],
        )

        report = render_markdown(assessment, "es")

        assert report.index("Major") < report.index("Minor")

    def test_the_client_name_appears_when_supplied(self):
        assessment = Assessment(assessment_id="a1", client="DGC")

        assert "DGC" in render_markdown(assessment, "es")

    def test_the_english_report_uses_english_headings(self):
        report = render_markdown(Assessment(assessment_id="a1"), "en")

        assert "Network audit report" in report
        assert "Findings" in report

    def test_a_chain_trace_is_rendered_with_its_hops(self):
        snapshot = NetworkSnapshot(
            devices=[
                DeviceSnapshot(
                    device=device("router", "10.0.0.254", 3),
                    arp=[
                        ArpEntry(
                            ip="10.0.0.50",
                            mac="00:AA:BB:CC:DD:EE",
                            interface="vlan1",
                            type="dynamic",
                        )
                    ],
                )
            ]
        )
        assessment = Assessment(
            assessment_id="a1",
            snapshot=snapshot,
            trace=trace_chain(snapshot, "10.0.0.50"),
        )

        report = render_markdown(assessment, "es")

        assert "Traza de conexión" in report
        assert "10.0.0.50" in report

    def test_an_empty_assessment_still_renders(self):
        report = render_markdown(Assessment(assessment_id="a1"), "es")

        assert "Informe de auditoría de red" in report
        assert "No se encontraron hallazgos" in report


class TestWriteReport:
    def test_markdown_is_written_to_the_requested_path(self, tmp_path):
        target = tmp_path / "nested" / "report.md"

        written = write_report(Assessment(assessment_id="a1"), target)

        assert written == target
        assert "Informe" in target.read_text(encoding="utf-8")

    def test_a_pdf_request_without_support_falls_back_to_markdown(self, tmp_path):
        """Losing the collected evidence over a missing renderer would be worse
        than handing over Markdown."""
        target = tmp_path / "report.pdf"

        written = write_report(Assessment(assessment_id="a1"), target)

        assert written.suffix in {".pdf", ".md"}
        assert written.exists()

    def test_the_locale_reaches_the_written_file(self, tmp_path):
        target = tmp_path / "report.md"

        write_report(Assessment(assessment_id="a1"), target, locale="en")

        assert "Network audit report" in target.read_text(encoding="utf-8")
