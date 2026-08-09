"""Tests for PDF rendering.

The PDF is what a client receives, so these check that the content survives the
conversion, that hostile text cannot break the document, and that a missing
renderer degrades instead of losing the collected evidence.
"""

from __future__ import annotations

import pytest

from lynjax.services.assessment import Assessment, render_markdown, write_report
from lynjax.services.audit import NetworkSnapshot
from lynjax.services.connectors.base import AuditCheck

reportlab = pytest.importorskip("reportlab")

from lynjax.services.pdf import (  # noqa: E402
    _inline,
    _is_separator,
    _split_row,
    markdown_to_flowables,
    markdown_to_pdf,
)


class TestInlineMarkup:
    def test_bold_becomes_reportlab_markup(self):
        assert _inline("**Cliente:** DGC") == "<b>Cliente:</b> DGC"

    def test_backticks_become_a_monospace_span(self):
        assert 'face="Courier"' in _inline("`10.0.0.50`")

    def test_angle_brackets_are_escaped(self):
        """Device names and banners are untrusted text; unescaped markup would
        either break the document or inject styling into a client's report."""
        assert _inline("switch <b>evil</b>") == "switch &lt;b&gt;evil&lt;/b&gt;"

    def test_ampersands_are_escaped(self):
        assert _inline("A & B") == "A &amp; B"


class TestTableParsing:
    def test_a_row_splits_into_cells(self):
        assert _split_row("| a | b | c |") == ["a", "b", "c"]

    def test_the_separator_row_is_recognised(self):
        assert _is_separator("|---|---|---|") is True
        assert _is_separator("| :--- | ---: |") is True

    def test_a_content_row_is_not_a_separator(self):
        assert _is_separator("| core-sw | 10.0.0.1 |") is False


class TestFlowables:
    def test_a_report_produces_flowables(self):
        markdown = render_markdown(Assessment(assessment_id="a1"), "es")

        assert markdown_to_flowables(markdown)

    def test_headings_tables_and_bullets_are_all_handled(self):
        markdown = "\n".join(
            [
                "# Title",
                "",
                "## Section",
                "",
                "| A | B |",
                "|---|---|",
                "| 1 | 2 |",
                "",
                "- first",
                "- second",
                "",
                "Plain paragraph.",
            ]
        )

        assert len(markdown_to_flowables(markdown)) >= 6

    def test_an_empty_document_yields_nothing_rather_than_raising(self):
        assert markdown_to_flowables("") == []

    def test_a_table_missing_its_separator_still_renders(self):
        flowables = markdown_to_flowables("| A | B |\n| 1 | 2 |")

        assert flowables


class TestPdfOutput:
    def test_a_pdf_file_is_produced(self, tmp_path):
        target = tmp_path / "report.pdf"

        markdown_to_pdf(render_markdown(Assessment(assessment_id="a1"), "es"), target)

        assert target.exists()
        assert target.read_bytes().startswith(b"%PDF-")

    def test_parent_directories_are_created(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "report.pdf"

        markdown_to_pdf("# Title", target)

        assert target.exists()

    def test_write_report_routes_a_pdf_suffix_to_the_renderer(self, tmp_path):
        target = tmp_path / "report.pdf"

        written = write_report(Assessment(assessment_id="a1"), target, locale="es")

        assert written == target
        assert written.read_bytes().startswith(b"%PDF-")

    def test_a_markdown_suffix_still_writes_markdown(self, tmp_path):
        target = tmp_path / "report.md"

        written = write_report(Assessment(assessment_id="a1"), target)

        assert written.read_text(encoding="utf-8").startswith("#")

    def test_a_full_report_with_findings_renders(self, tmp_path):
        assessment = Assessment(
            assessment_id="a1",
            client="DGC",
            snapshot=NetworkSnapshot(),
            findings=[
                AuditCheck(
                    name="Duplicate IP address",
                    status="fail",
                    message="10.0.0.77 answers to 2 different MAC addresses.",
                ),
                AuditCheck(
                    name="Interface errors", status="warning", message="4820 errors."
                ),
            ],
            unreachable=[("edge-fw", "timed out")],
        )
        target = tmp_path / "full.pdf"

        write_report(assessment, target, locale="es")

        assert target.stat().st_size > 1500

    def test_hostile_device_names_do_not_break_the_document(self, tmp_path):
        """A device name is operator-supplied text and reaches the PDF."""
        assessment = Assessment(
            assessment_id="a1",
            client="<script>alert(1)</script> & Co",
            findings=[
                AuditCheck(name="<b>x</b>", status="fail", message="a < b & c > d")
            ],
        )
        target = tmp_path / "hostile.pdf"

        write_report(assessment, target, locale="es")

        assert target.read_bytes().startswith(b"%PDF-")
