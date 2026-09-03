import datetime
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
)

from .. import models


def build_report(scan: models.Scan, image_bytes: bytes | None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom", parent=styles["Title"], fontSize=16, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=14
    )

    story = [
        Paragraph("Legal Metrology Compliance Report", title_style),
        Paragraph(
            "Generated under the Legal Metrology (Packaged Commodities) Rules, 2011 "
            "&mdash; automated screening prototype",
            subtitle_style,
        ),
    ]

    status_color = colors.HexColor("#15803d") if scan.status.value == "compliant" else colors.HexColor("#b91c1c")
    meta_table = Table(
        [
            ["Product", scan.product_name],
            ["Brand", scan.brand_name or "-"],
            ["Category", scan.category or "-"],
            ["Scan ID", str(scan.id)],
            ["Scanned on", scan.created_at.strftime("%d %b %Y, %H:%M UTC")],
            ["Overall status", scan.status.value.replace("_", " ").upper()],
            ["Compliance score", f"{scan.overall_score}%"],
        ],
        colWidths=[45 * mm, 120 * mm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (1, 5), (1, 5), status_color),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10 * mm))

    if image_bytes:
        try:
            img = RLImage(io.BytesIO(image_bytes), width=70 * mm, height=70 * mm, kind="proportional")
            story.append(img)
            story.append(Spacer(1, 8 * mm))
        except Exception:
            pass

    story.append(Paragraph("Declaration Checklist", styles["Heading2"]))
    header = ["Declaration", "Rule", "Found", "Status", "Notes"]
    rows = [header]
    for d in scan.declarations:
        rows.append(
            [
                Paragraph(d.label, styles["Normal"]),
                d.rule_ref,
                "Yes" if d.found else "No",
                "COMPLIANT" if d.compliant else "VIOLATION",
                Paragraph(d.issue or "-", styles["Normal"]),
            ]
        )

    table = Table(rows, colWidths=[45 * mm, 28 * mm, 15 * mm, 22 * mm, 55 * mm], repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, d in enumerate(scan.declarations, start=1):
        color = colors.HexColor("#dcfce7") if d.compliant else colors.HexColor("#fee2e2")
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), color))
    table.setStyle(TableStyle(style_cmds))
    story.append(table)
    story.append(Spacer(1, 8 * mm))

    if scan.notes:
        story.append(Paragraph("AI-Assisted Summary", styles["Heading2"]))
        story.append(Paragraph(scan.notes, styles["Normal"]))
        story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            f"Report generated on {datetime.datetime.utcnow().strftime('%d %b %Y %H:%M UTC')} "
            "by the automated Legal Metrology compliance screening prototype. This report is "
            "indicative and intended to assist, not replace, human inspection and legal review.",
            ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
        )
    )

    doc.build(story)
    return buffer.getvalue()
