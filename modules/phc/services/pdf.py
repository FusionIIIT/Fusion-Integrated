from html import escape
from io import BytesIO
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from core.api.exceptions import BadRequestError, NotFoundError
from modules.phc.selectors import scoping

UNICODE_FONT_PATHS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
)


def _register_unicode_font() -> str:
    font_name = "PHCUnicode"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    font_path = next((path for path in UNICODE_FONT_PATHS if path.is_file()), None)
    if font_path is None:
        raise RuntimeError(
            "Install DejaVu Sans or FreeSans to enable Unicode PHC PDF exports.")
    pdfmetrics.registerFont(TTFont(font_name, str(font_path), shapable=True))
    return font_name


def _paragraph_text(value: str) -> str:
    return escape(value).replace("\n", "<br/>")


def _document_styles():
    font_name = _register_unicode_font()
    styles = getSampleStyleSheet()
    for style_name in ("Title", "Heading2", "Heading3", "BodyText"):
        styles[style_name].fontName = font_name
    styles.add(ParagraphStyle(
        name="PHCVisitDate", parent=styles["Heading2"], fontSize=12,
        leading=15, textColor=colors.HexColor("#1f4b5c"), spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        name="PHCBody", parent=styles["BodyText"], alignment=TA_LEFT,
        fontSize=10, leading=14, spaceAfter=2 * mm,
    ))
    return styles


def patient_records_pdf(*, actor, visit_ids: list[int]) -> bytes:
    visits = list(
        scoping.visits_for(actor).filter(pk__in=visit_ids)
        .prefetch_related("prescriptions").order_by("visited_on", "id")
    )
    if len(visits) != len(visit_ids):
        raise NotFoundError("One or more selected visits are not in your medical history.",
                            code="record_not_found")
    if len({visit.patient_user_id for visit in visits}) != 1:
        raise BadRequestError("Select visits belonging to one patient for a single PDF.",
                              code="mixed_patient_records")
    if not visits:
        raise BadRequestError("Select at least one medical visit to export.",
                              code="records_required")

    styles = _document_styles()
    first = visits[0]
    content = [
        Paragraph("Primary Health Centre — Medical Record", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph(f"Patient identifier: {first.patient_user_id}", styles["PHCBody"]),
        Paragraph(f"Generated: {timezone.localtime().strftime('%Y-%m-%d %H:%M %Z')}",
                  styles["PHCBody"]),
        Spacer(1, 5 * mm),
    ]
    for visit in visits:
        parts = [
            Paragraph(f"Visit date: {visit.visited_on.isoformat()}", styles["PHCVisitDate"]),
            Paragraph("Clinical notes", styles["Heading3"]),
            Paragraph(_paragraph_text(visit.notes), styles["PHCBody"]),
        ]
        prescriptions = sorted(visit.prescriptions.all(),
                               key=lambda row: (row.issued_on, row.pk))
        if prescriptions:
            parts.append(Paragraph("Prescriptions", styles["Heading3"]))
            parts.extend(
                Paragraph(
                    f"Issued {prescription.issued_on.isoformat()}: "
                    f"{_paragraph_text(prescription.details)}", styles["PHCBody"])
                for prescription in prescriptions
            )
        content.append(KeepTogether(parts))
        content.append(Spacer(1, 5 * mm))

    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Primary Health Centre medical record",
        author="Primary Health Centre",
        pageCompression=0,
    )
    document.build(content)
    return output.getvalue()
