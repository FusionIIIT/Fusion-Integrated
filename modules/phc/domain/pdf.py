"""A dependency-free single-font PDF writer for a patient's own records (PHC-UC-03)."""
from __future__ import annotations

import textwrap
from collections.abc import Sequence

LINES_PER_PAGE = 52
# Helvetica at 11 pt across a 512-pt text block fits about 90 characters.
WRAP_AT = 90


def printable(text: str) -> bool:
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        return False
    return True


def wrap(lines: Sequence[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        indent = line[:len(line) - len(line.lstrip())]
        out.extend(textwrap.wrap(line, WRAP_AT, subsequent_indent=indent + "  ",
                                 break_long_words=True) or [""])
    return out


def _literal(value: object) -> str:
    text = " ".join(str(value or "").split())
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_stream(lines: Sequence[str]) -> bytes:
    stream = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index:
            stream.append("T*")
        stream.append(f"({_literal(line)}) Tj")
    stream.append("ET")
    return "\n".join(stream).encode("latin-1")


def render(lines: Sequence[str]) -> bytes:
    lines = wrap(lines)
    pages = [lines[i:i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)]
    if not pages:
        pages = [[]]
    first_page = 4
    kids = " ".join(f"{first_page + 2 * i} 0 R" for i in range(len(pages)))
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, page in enumerate(pages):
        content = _page_stream(page)
        objects.append(
            (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
             f"/Resources << /Font << /F1 3 0 R >> >> /Contents {first_page + 2 * i + 1} 0 R >>"
             ).encode())
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
                       + content + b"\nendstream")
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_at = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
    output.extend(f"startxref\n{xref_at}\n%%EOF\n".encode())
    return bytes(output)
