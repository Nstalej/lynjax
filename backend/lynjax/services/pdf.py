"""Markdown to PDF rendering for assessment reports.

Built on ReportLab, which is pure Python and ships as a wheel on every
platform. WeasyPrint produces prettier output but needs GTK, Cairo and Pango
installed system-wide, and on Windows that is exactly the kind of friction that
would undermine the point of an installable field tool.

Only the subset of Markdown the report generator emits is handled: headings,
paragraphs, bullet lists, tables and bold spans. This is a renderer for our own
output, not a general Markdown implementation, and pretending otherwise would
invite silent misrenders of things we never produce.
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Lynjax brand colours, from brand/tokens/lynjax-colors.json.
DEEP_NAVY = colors.HexColor("#083B5C")
SIGNAL_BLUE = colors.HexColor("#0E7490")
TRACE_TEAL = colors.HexColor("#2DD4BF")
SLATE_TEXT = colors.HexColor("#0F172A")
MUTED_LINE = colors.HexColor("#B7CDD1")
ICE_BACKGROUND = colors.HexColor("#F2FAF8")

#: Severity labels carry colour so a reader scanning the PDF finds the
#: critical findings without reading every heading.
SEVERITY_COLOURS = {
    "Crítico": colors.HexColor("#B91C1C"),
    "Critical": colors.HexColor("#B91C1C"),
    "Atención": colors.HexColor("#B45309"),
    "Attention": colors.HexColor("#B45309"),
    "Correcto": SIGNAL_BLUE,
    "OK": SIGNAL_BLUE,
}

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")
_SEVERITY_HEADING = re.compile(r"^\[([^\]]+)\]\s*(.*)$")


def _inline(text: str) -> str:
    """Convert inline Markdown to ReportLab markup, escaping everything else."""
    escaped = xml_escape(text)
    escaped = _BOLD.sub(r"<b>\1</b>", escaped)
    escaped = _CODE.sub(r'<font face="Courier">\1</font>', escaped)
    return escaped


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "LynjaxTitle",
            parent=base["Title"],
            fontSize=22,
            leading=26,
            textColor=DEEP_NAVY,
            spaceAfter=4 * mm,
            alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "LynjaxH2",
            parent=base["Heading2"],
            fontSize=14,
            leading=18,
            textColor=DEEP_NAVY,
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
        ),
        "h3": ParagraphStyle(
            "LynjaxH3",
            parent=base["Heading3"],
            fontSize=11.5,
            leading=15,
            textColor=SLATE_TEXT,
            spaceBefore=4 * mm,
            spaceAfter=1.5 * mm,
        ),
        "body": ParagraphStyle(
            "LynjaxBody",
            parent=base["BodyText"],
            fontSize=9.5,
            leading=13.5,
            textColor=SLATE_TEXT,
            spaceAfter=1.5 * mm,
        ),
        "cell": ParagraphStyle(
            "LynjaxCell",
            parent=base["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=SLATE_TEXT,
        ),
        "cell_header": ParagraphStyle(
            "LynjaxCellHeader",
            parent=base["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        ),
    }


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(line: str) -> bool:
    stripped = line.strip().strip("|").replace(" ", "")
    return bool(stripped) and set(stripped) <= {"-", ":", "|"}


def _build_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    header, *body = rows
    data = [[Paragraph(_inline(cell), styles["cell_header"]) for cell in header]]
    data += [[Paragraph(_inline(cell), styles["cell"]) for cell in row] for row in body]

    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DEEP_NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ICE_BACKGROUND]),
                ("GRID", (0, 0), (-1, -1), 0.4, MUTED_LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _heading_flowable(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    """Render an H3, colouring the severity label when the heading carries one."""
    match = _SEVERITY_HEADING.match(text)
    if not match:
        return Paragraph(_inline(text), styles["h3"])

    label, rest = match.groups()
    colour = SEVERITY_COLOURS.get(label, SLATE_TEXT)
    return Paragraph(
        f'<font color="{colour.hexval()}"><b>[{xml_escape(label)}]</b></font> '
        f"{_inline(rest)}",
        styles["h3"],
    )


def markdown_to_flowables(markdown: str) -> list:
    """Turn the report Markdown into ReportLab flowables."""
    styles = _styles()
    flowables: list = []
    pending_table: list[list[str]] = []
    pending_bullets: list[str] = []

    def flush_table() -> None:
        nonlocal pending_table
        if pending_table:
            flowables.append(_build_table(pending_table, styles))
            flowables.append(Spacer(1, 3 * mm))
            pending_table = []

    def flush_bullets() -> None:
        nonlocal pending_bullets
        if pending_bullets:
            flowables.append(
                ListFlowable(
                    [
                        ListItem(Paragraph(_inline(item), styles["body"]))
                        for item in pending_bullets
                    ],
                    bulletType="bullet",
                    bulletColor=SIGNAL_BLUE,
                    leftIndent=6 * mm,
                )
            )
            flowables.append(Spacer(1, 2 * mm))
            pending_bullets = []

    for raw in markdown.splitlines():
        line = raw.rstrip()

        if line.startswith("|"):
            flush_bullets()
            if not _is_separator(line):
                pending_table.append(_split_row(line))
            continue

        flush_table()

        if not line.strip():
            flush_bullets()
            continue

        if line.startswith("- "):
            pending_bullets.append(line[2:])
            continue

        flush_bullets()

        if line.startswith("### "):
            flowables.append(_heading_flowable(line[4:], styles))
        elif line.startswith("## "):
            flowables.append(Paragraph(_inline(line[3:]), styles["h2"]))
        elif line.startswith("# "):
            flowables.append(Paragraph(_inline(line[2:]), styles["title"]))
            flowables.append(
                Table(
                    [[""]],
                    colWidths=[170 * mm],
                    rowHeights=[1.2 * mm],
                    style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), TRACE_TEAL)]),
                    hAlign="LEFT",
                )
            )
            flowables.append(Spacer(1, 4 * mm))
        else:
            flowables.append(Paragraph(_inline(line), styles["body"]))

    flush_table()
    flush_bullets()
    return flowables


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SIGNAL_BLUE)
    canvas.drawString(20 * mm, 12 * mm, "Lynjax — Intelligent Network Visibility")
    canvas.drawRightString(190 * mm, 12 * mm, f"{doc.page}")
    canvas.setStrokeColor(MUTED_LINE)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


def markdown_to_pdf(markdown: str, path: Path, *, title: str = "Lynjax") -> Path:
    """Render report Markdown to a PDF at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)

    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=title,
        author="Lynjax",
    )
    document.build(
        markdown_to_flowables(markdown), onFirstPage=_footer, onLaterPages=_footer
    )
    return path


__all__ = ["markdown_to_pdf", "markdown_to_flowables", "PageBreak", "KeepTogether"]
