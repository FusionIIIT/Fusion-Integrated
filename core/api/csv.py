"""CSV export that cannot execute on the recipient's machine.

Excel, Sheets and LibreOffice treat a cell beginning `=`, `+`, `-`, `@`, tab or
CR as a formula. A student called `=cmd|'/c calc'!A1` therefore runs as code
the moment a TPO opens the export. Escaping happens here rather than at each
call site, so a new export cannot forget it (threat model 4.10).

Rows stream, so a 3,000-row export never materialises in memory.
"""
from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from typing import Any

from django.http import StreamingHttpResponse

#: Leading characters a spreadsheet reads as the start of a formula.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class _Echo:
    """A file-like object that returns what it is given, so csv.writer can be
    driven from a generator instead of a buffer."""

    def write(self, value: str) -> str:
        return value


def sanitise_cell(value: Any) -> str:
    """Render a value as text a spreadsheet will not evaluate."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(FORMULA_PREFIXES):
        # A leading apostrophe means "text"; quoting alone does not stop evaluation.
        return "'" + text
    return text


def _rows(header: list[str], rows: Iterable[Iterable[Any]]) -> Iterator[str]:
    writer = csv.writer(_Echo())
    yield writer.writerow(header)
    for row in rows:
        yield writer.writerow([sanitise_cell(cell) for cell in row])


def stream(*, filename: str, header: list[str],
           rows: Iterable[Iterable[Any]]) -> StreamingHttpResponse:
    """A downloadable CSV. `rows` may be a generator or a queryset iterator."""
    response = StreamingHttpResponse(
        _rows(header, rows), content_type="text/csv; charset=utf-8")
    # Only characters that cannot break the header; the caller builds the name.
    safe = "".join(c for c in filename if c.isalnum() or c in "._-")
    response["Content-Disposition"] = f'attachment; filename="{safe}"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response
