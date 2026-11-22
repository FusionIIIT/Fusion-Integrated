"""Leave-day counting (CFR-EL-010, BR-EL-010, BR-EL-011).

Two counting regimes and the spec draws the line exactly: EL/COL/VL count
continuously across weekends and closed holidays; CL/SCL/RH do not. RH is
narrower still — it counts only days the published calendar marks restricted.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain import categories as cat


class CountingError(Exception):
    """Raised when a period cannot be counted at all."""


def _span(start: date, end: date) -> list[date]:
    if end < start:
        raise CountingError("The end date falls before the start date.")
    out, cursor = [], start
    while cursor <= end:
        out.append(cursor)
        cursor += timedelta(days=1)
    return out


def count_days(category: str, start: date, end: date, *,
               holidays: set[date] | None = None,
               restricted_holidays: set[date] | None = None,
               half_day: bool = False) -> Decimal:
    """The leave days a period costs, as an exact Decimal.

    Half days are a CL-only concept (BR-EL-010) and are rejected elsewhere
    rather than silently rounded, because a half EL is not a thing.
    """
    closed = holidays or set()
    restricted = restricted_holidays or set()

    if half_day and category != cat.CASUAL:
        raise CountingError(
            "A half-day request is only available for Casual Leave.")

    if cat.is_continuous(category):
        days = Decimal(len(_span(start, end)))
    elif category == cat.RESTRICTED_HOLIDAY:
        if not restricted:
            raise CountingError(
                "No published Restricted Holiday calendar is available to check "
                "this request against.")
        days = Decimal(sum(1 for d in _span(start, end) if d in restricted))
    else:
        days = Decimal(sum(1 for d in _span(start, end)
                            if d.weekday() < 5 and d not in closed))

    if half_day:
        days = Decimal(cat.HALF_DAY_COST)

    if days <= 0:
        raise CountingError(
            "This period contains no leave days: it is entirely weekends, "
            "closed holidays, or outside the applicable calendar.")
    return days