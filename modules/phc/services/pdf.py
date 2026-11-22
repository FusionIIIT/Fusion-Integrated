"""Small dependency-free PDF export for patient-owned PHC visit records."""

from __future__ import annotations

import re


def _pdf_escape(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"[^\x20-\x7e]", "?", text)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_visits_pdf(visits) -> bytes:
    """Render visit and prescription summaries into a valid, printable PDF."""
    lines = ["Primary Health Centre - Medical Records", ""]
    for visit in visits:
        lines.extend(
            [
                f"Visit date: {visit.visit_date}",
                f"Chief complaint: {visit.chief_complaint}",
                f"Diagnosis: {visit.diagnosis or 'Not recorded'}",
                f"Notes: {visit.notes or 'None'}",
            ]
        )
        for rx in visit.prescriptions.all():
            lines.append(
                f"Prescription: {rx.medicine_name}; dosage: {rx.dosage}; "
                f"duration (days): {rx.duration_days or 'Not specified'}"
            )
            if rx.instructions:
                lines.append(f"Instructions: {rx.instructions}")
        lines.append("")

    # Split long lines, then paginate at a conservative number of lines.
    wrapped = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        wrapped.extend(line[i : i + 88] for i in range(0, len(line), 88))
    pages = [wrapped[i : i + 48] for i in range(0, len(wrapped), 48)] or [[]]

    objects: list[bytes] = []
    page_ids = []
    font_id = 3 + 2 * len(pages)
    for index, page_lines in enumerate(pages):
        page_id = 3 + 2 * index
        stream_id = page_id + 1
        page_ids.append(page_id)
        commands = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
        for line in page_lines:
            commands.extend([f"({_pdf_escape(line)}) Tj", "T*"])
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects.extend(
            [
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                    f"/Contents {stream_id} 0 R >>"
                ).encode("ascii"),
                b"<< /Length "
                + str(len(stream)).encode("ascii")
                + b" >>\nstream\n"
                + stream
                + b"\nendstream",
            ]
        )

    catalog = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_object = (f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>").encode("ascii")
    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    all_objects = [catalog, pages_object, *objects, font]

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(all_objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)
