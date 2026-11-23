"""Query parameters are hostile input: anything unusable is a 400, never a 500."""

from __future__ import annotations

import datetime

from core.api.exceptions import BadRequestError

MAX_ID = 2**63 - 1


def int_param(request, name: str) -> int | None:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    if not raw.isascii() or not raw.isdigit() or int(raw[:20]) > MAX_ID:
        raise BadRequestError(f"{name} must be a whole number.", code="invalid_filter")
    return int(raw)


def date_param(request, name: str) -> datetime.date | None:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError as exc:
        raise BadRequestError(
            f"{name} must be a date such as 2026-12-31.", code="invalid_filter"
        ) from exc


def text_param(request, name: str) -> str:
    # PostgreSQL refuses a NUL in text, which would surface as a 500.
    return request.query_params.get(name, "").replace("\x00", "").strip()
