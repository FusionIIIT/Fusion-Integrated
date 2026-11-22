"""A minimal, dependency-free PDF table writer (AFR-152, UC-007).

Reports export as CSV or PDF. No PDF library is installed, and a new dependency needs
approval, so this writes the small subset of PDF 1.4 a report needs: A4 landscape pages,
a title, a repeated header row, fixed-width columns, and a page footer. Text uses the
built-in Helvetica fonts, so nothing is embedded and the output is deterministic.

Limits, stated so nobody is surprised: text outside Latin-1 is replaced with ``?``, cells
longer than their column are cut with ``..``, and there is no wrapping. That is enough for
an operational report; a designed document would need a real library.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

PAGE_W, PAGE_H = 842, 595            # A4 landscape, in points
MARGIN = 36
FONT_SIZE = 8
LEADING = 11
TITLE_SIZE = 13
#: Average Helvetica glyph width as a fraction of the font size. Slightly generous so a
#: full cell does not touch the next column.
_GLYPH = 0.55
_TOP_BLOCK = TITLE_SIZE + 2 * LEADING          # title, subtitle, gap
_FOOTER = 2 * LEADING


def _clean(value: Any) -> str:
    """Text safe to place inside a PDF string literal."""
    text = "" if value is None else str(value)
    text = " ".join(text.split())                       # newlines/tabs become spaces
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _fit(text: str, max_chars: int) -> str:
    """Cut to ``max_chars`` visible characters without splitting an escape sequence."""
    raw = text.replace("\\\\", "\\").replace("\\(", "(").replace("\\)", ")")
    if len(raw) <= max_chars:
        return text
    return _clean(raw[:max(max_chars - 2, 0)] + "..")


def _page_stream(title: str, subtitle: str, header: Sequence[str],
                 rows: Sequence[Sequence[Any]], page: int, pages: int,
                 col_w: float, max_chars: int) -> bytes:
    y = PAGE_H - MARGIN
    out = [f"BT /F2 {TITLE_SIZE} Tf {MARGIN} {y} Td ({_clean(title)}) Tj ET"]
    y -= TITLE_SIZE + 4
    if subtitle:
        out.append(f"BT /F1 {FONT_SIZE} Tf {MARGIN} {y} Td ({_clean(subtitle)}) Tj ET")
    y -= 2 * LEADING

    def line(cells: Iterable[Any], font: str, ypos: float) -> str:
        parts = [f"BT /{font} {FONT_SIZE} Tf {MARGIN} {ypos} Td"]
        last = 0.0
        for i, cell in enumerate(cells):
            x = i * col_w
            parts.append(f"{x - last:.2f} 0 Td ({_fit(_clean(cell), max_chars)}) Tj")
            last = x
        parts.append("ET")
        return " ".join(parts)

    out.append(line(header, "F2", y))
    out.append(f"{MARGIN} {y - 3} m {PAGE_W - MARGIN} {y - 3} l S")
    y -= LEADING
    for row in rows:
        out.append(line(row, "F1", y))
        y -= LEADING
    out.append(f"BT /F1 {FONT_SIZE} Tf {PAGE_W - MARGIN - 60} {MARGIN - 14} Td "
               f"(Page {page} of {pages}) Tj ET")
    return "\n".join(out).encode("latin-1")


def render_table(*, title: str, header: Sequence[str], rows: Iterable[Sequence[Any]],
                 subtitle: str = "") -> bytes:
    """A PDF document holding ``header`` and ``rows`` as a table. Returns the file bytes."""
    header = list(header) or [""]
    body = [list(r) for r in rows]
    ncols = len(header)
    col_w = (PAGE_W - 2 * MARGIN) / ncols
    max_chars = max(int(col_w / (FONT_SIZE * _GLYPH)) - 1, 3)
    per_page = max(int((PAGE_H - 2 * MARGIN - _TOP_BLOCK - _FOOTER) // LEADING), 1)
    chunks = [body[i:i + per_page] for i in range(0, len(body), per_page)] or [[]]

    # Object numbers: 1 catalog, 2 pages, 3 and 4 fonts, then (page, content) pairs.
    objects: dict[int, bytes] = {
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>"),
    }
    kids = []
    for n, chunk in enumerate(chunks, start=1):
        page_no, content_no = 3 + 2 * n, 4 + 2 * n
        stream = _page_stream(title, subtitle, header, chunk, n, len(chunks), col_w, max_chars)
        objects[content_no] = (b"<< /Length %d >>\nstream\n" % len(stream)
                               + stream + b"\nendstream")
        objects[page_no] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_no} 0 R >>").encode("latin-1")
        kids.append(f"{page_no} 0 R")
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = (f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
                  .encode("latin-1"))

    buf = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in sorted(objects):
        offsets[num] = len(buf)
        buf += b"%d 0 obj\n" % num + objects[num] + b"\nendobj\n"
    xref_at = len(buf)
    size = max(objects) + 1
    buf += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for num in range(1, size):
        buf += b"%010d 00000 n \n" % offsets[num]
    buf += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (size, xref_at))
    return bytes(buf)
