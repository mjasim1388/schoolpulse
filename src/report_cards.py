import base64
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)


# ============================================================
# COLORS
# ============================================================
INDIGO = colors.HexColor("#4338ca")
AMBER = colors.HexColor("#f59e0b")
SLATE_700 = colors.HexColor("#334155")
SLATE_500 = colors.HexColor("#64748b")
SLATE_200 = colors.HexColor("#e2e8f0")
SLATE_50 = colors.HexColor("#f8fafc")
GREEN = colors.HexColor("#059669")
RED = colors.HexColor("#dc2626")


def _safe(text):
    """Strip non-latin characters that would break the default font."""
    if text is None:
        return ""
    text = str(text)
    return "".join(ch if ord(ch) < 256 else "?" for ch in text)


def _grade_for(percentage):
    if percentage >= 90:
        return "A+"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B"
    if percentage >= 60:
        return "C"
    if percentage >= 50:
        return "D"
    if percentage >= 40:
        return "E"
    return "F"


def _subject_grade(pct):
    if pct >= 90:
        return "A+"
    if pct >= 80:
        return "A"
    if pct >= 70:
        return "B"
    if pct >= 60:
        return "C"
    if pct >= 50:
        return "D"
    if pct >= 40:
        return "E"
    return "F"


def _make_styles():
    return {
        "school_name": ParagraphStyle(
            "school_name", fontName="Helvetica-Bold", fontSize=18,
            textColor=INDIGO, alignment=TA_CENTER, leading=22,
        ),
        "school_meta": ParagraphStyle(
            "school_meta", fontName="Helvetica", fontSize=9,
            textColor=SLATE_500, alignment=TA_CENTER, leading=12,
        ),
        "title": ParagraphStyle(
            "title", fontName="Helvetica-Bold", fontSize=14,
            textColor=SLATE_700, alignment=TA_CENTER, leading=18,
            spaceBefore=4, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName="Helvetica", fontSize=10,
            textColor=SLATE_500, alignment=TA_CENTER, leading=13,
        ),
        "label": ParagraphStyle(
            "label", fontName="Helvetica-Bold", fontSize=9,
            textColor=SLATE_500, leading=11,
        ),
        "value": ParagraphStyle(
            "value", fontName="Helvetica", fontSize=10,
            textColor=SLATE_700, leading=13,
        ),
        "cell": ParagraphStyle(
            "cell", fontName="Helvetica", fontSize=9,
            textColor=SLATE_700, leading=11,
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold", fontName="Helvetica-Bold", fontSize=9,
            textColor=SLATE_700, leading=11,
        ),
        "cell_center": ParagraphStyle(
            "cell_center", fontName="Helvetica", fontSize=9,
            textColor=SLATE_700, alignment=TA_CENTER, leading=11,
        ),
        "cell_center_bold": ParagraphStyle(
            "cell_center_bold", fontName="Helvetica-Bold", fontSize=9,
            textColor=SLATE_700, alignment=TA_CENTER, leading=11,
        ),
        "header_cell": ParagraphStyle(
            "header_cell", fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.white, alignment=TA_CENTER, leading=11,
        ),
        "small": ParagraphStyle(
            "small", fontName="Helvetica", fontSize=8,
            textColor=SLATE_500, leading=10,
        ),
        "footer_label": ParagraphStyle(
            "footer_label", fontName="Helvetica", fontSize=9,
            textColor=SLATE_500, alignment=TA_CENTER, leading=11,
        ),
    }


def build_report_card_pdf(report_data, school_profile):
    """
    Build one report card PDF.
    Returns bytes of the PDF.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Report Card - {report_data['student']['full_name']}",
    )

    styles = _make_styles()
    story = []

    # ---------------- HEADER ----------------
    header_table_data = []

    logo_b64 = (school_profile or {}).get("logo_base64")
    school_name = (school_profile or {}).get("school_name") or "My School"
    address = (school_profile or {}).get("address") or ""
    phone = (school_profile or {}).get("phone") or ""
    email = (school_profile or {}).get("email") or ""

    meta_bits = [b for b in [address, phone, email] if b]
    meta_line = "  ·  ".join(_safe(b) for b in meta_bits)

    logo_flowable = None
    if logo_b64:
        try:
            logo_bytes = base64.b64decode(logo_b64)
            logo_flowable = Image(BytesIO(logo_bytes), width=18 * mm, height=18 * mm)
        except Exception:
            logo_flowable = None

    if logo_flowable:
        # Layout: [logo]  [school name + meta]
        inner = [
            [Paragraph(_safe(school_name), styles["school_name"])],
            [Paragraph(meta_line, styles["school_meta"])],
        ]
        inner_table = Table(inner, colWidths=[140 * mm])
        inner_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        header_table_data.append([
            [logo_flowable, inner_table]
        ])
    else:
        header_table_data.append([
            Paragraph(_safe(school_name), styles["school_name"])
        ])
        if meta_line:
            header_table_data.append([Paragraph(meta_line, styles["school_meta"])])

    header_table = Table(header_table_data, colWidths=[174 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)

    # Divider
    divider = Table([[""]], colWidths=[174 * mm], rowHeights=[0.6])
    divider.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 0.8, INDIGO),
    ]))
    story.append(divider)
    story.append(Spacer(1, 6))

    # ---------------- TITLE ----------------
    story.append(Paragraph("REPORT CARD", styles["title"]))
    exam_name = _safe(report_data.get("exam_name") or "")
    term = _safe(report_data.get("term") or "")
    if term and term not in exam_name:
        story.append(Paragraph(f"{exam_name} · {term}", styles["subtitle"]))
    else:
        story.append(Paragraph(exam_name, styles["subtitle"]))
    story.append(Spacer(1, 10))

    # ---------------- STUDENT INFO ----------------
    s = report_data["student"]

    def lab(t):
        return Paragraph(_safe(t), styles["label"])

    def val(t):
        return Paragraph(_safe(t), styles["value"])

    info_rows = [
        [lab("Student name"), val(s.get("full_name", "")),
         lab("Roll number"), val(s.get("roll_number", "") or "—")],
        [lab("Class"), val(f"{s.get('class_name','')} {s.get('section','') or ''}".strip()),
         lab("Section"), val(s.get("section", "") or "—")],
        [lab("Parent / guardian"), val(s.get("parent_name", "") or "—"),
         lab("Contact"), val(s.get("parent_phone", "") or "—")],
    ]

    info_table = Table(
        info_rows,
        colWidths=[32 * mm, 55 * mm, 30 * mm, 57 * mm],
    )
    info_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, SLATE_200),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
        ("BACKGROUND", (0, 0), (0, -1), SLATE_50),
        ("BACKGROUND", (2, 0), (2, -1), SLATE_50),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # ---------------- MARKS TABLE ----------------
    table_data = [[
        Paragraph("Subject", styles["header_cell"]),
        Paragraph("Marks", styles["header_cell"]),
        Paragraph("Max", styles["header_cell"]),
        Paragraph("%", styles["header_cell"]),
        Paragraph("Grade", styles["header_cell"]),
        Paragraph("Result", styles["header_cell"]),
    ]]

    for sub in report_data["subjects"]:
        if sub["is_absent"]:
            row = [
                Paragraph(_safe(sub["subject_name"]), styles["cell"]),
                Paragraph("Absent", styles["cell_center"]),
                Paragraph(str(sub["max_marks"]), styles["cell_center"]),
                Paragraph("—", styles["cell_center"]),
                Paragraph("—", styles["cell_center"]),
                Paragraph("Absent", styles["cell_center"]),
            ]
        else:
            result_text = "Pass" if sub["passed"] else "Fail"
            result_color = GREEN if sub["passed"] else RED
            result_style = ParagraphStyle(
                "r", parent=styles["cell_center_bold"],
                textColor=result_color,
            )
            row = [
                Paragraph(_safe(sub["subject_name"]), styles["cell"]),
                Paragraph(f"{sub['marks_obtained']:.0f}", styles["cell_center"]),
                Paragraph(str(sub["max_marks"]), styles["cell_center"]),
                Paragraph(f"{sub['percentage']:.1f}", styles["cell_center"]),
                Paragraph(_subject_grade(sub["percentage"]), styles["cell_center_bold"]),
                Paragraph(result_text, result_style),
            ]
        table_data.append(row)

    marks_table = Table(
        table_data,
        colWidths=[70 * mm, 20 * mm, 20 * mm, 20 * mm, 22 * mm, 22 * mm],
        repeatRows=1,
    )
    marks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, SLATE_200),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(marks_table)
    story.append(Spacer(1, 12))

    # ---------------- SUMMARY BOX ----------------
    percentage = report_data["percentage"]
    grade = report_data["grade"]
    position = report_data.get("position")
    total_in_class = report_data.get("total_in_class") or 0

    pos_text = (
        f"{position} of {total_in_class}"
        if position and total_in_class else "—"
    )

    summary_rows = [
        [
            Paragraph("Total marks", styles["label"]),
            Paragraph(f"{report_data['total_obtained']:.0f} / {report_data['total_max']}",
                      styles["value"]),
            Paragraph("Percentage", styles["label"]),
            Paragraph(f"{percentage:.1f}%", styles["value"]),
        ],
        [
            Paragraph("Grade", styles["label"]),
            Paragraph(grade, styles["cell_bold"]),
            Paragraph("Position", styles["label"]),
            Paragraph(pos_text, styles["value"]),
        ],
        [
            Paragraph("Subjects passed", styles["label"]),
            Paragraph(str(report_data.get("subjects_passed", 0)), styles["value"]),
            Paragraph("Subjects failed", styles["label"]),
            Paragraph(str(report_data.get("subjects_failed", 0)), styles["value"]),
        ],
    ]

    summary_table = Table(
        summary_rows,
        colWidths=[35 * mm, 52 * mm, 35 * mm, 52 * mm],
    )
    summary_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, SLATE_200),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
        ("BACKGROUND", (0, 0), (0, -1), SLATE_50),
        ("BACKGROUND", (2, 0), (2, -1), SLATE_50),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 18))

    # ---------------- FOOTER (signatures) ----------------
    sig_data = [[
        Paragraph("_______________________", styles["footer_label"]),
        Paragraph("_______________________", styles["footer_label"]),
        Paragraph("_______________________", styles["footer_label"]),
    ], [
        Paragraph("Class teacher", styles["footer_label"]),
        Paragraph("Principal", styles["footer_label"]),
        Paragraph("Parent / guardian", styles["footer_label"]),
    ]]
    sig_table = Table(sig_data, colWidths=[58 * mm, 58 * mm, 58 * mm])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(sig_table)

    # ---------------- BUILD ----------------
    doc.build(story)
    return buf.getvalue()


def build_bulk_zip(report_cards_data, school_profile):
    """
    Given a list of report_data dicts, build a ZIP of PDFs.
    Returns bytes of the ZIP file.
    """
    import zipfile
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rd in report_cards_data:
            pdf_bytes = build_report_card_pdf(rd, school_profile)
            roll = rd["student"].get("roll_number") or "no-roll"
            name = rd["student"].get("full_name", "student")
            safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
            filename = f"{roll}_{safe_name}.pdf"
            zf.writestr(filename, pdf_bytes)
    return zip_buf.getvalue()