"""Chargeable leave days (BR-EL-010, BR-EL-011)."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain import categories as cat

FULL, FIRST_HALF, SECOND_HALF = "", "first", "second"
HALVES = (FULL, FIRST_HALF, SECOND_HALF)


def days_between(start: date, end: date) -> Iterator[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def chargeable_days(category: str, start: date, end: date, *, half: str = FULL,
                    closed_holidays: frozenset[date] = frozenset(),
                    weekend_days: frozenset[int] = frozenset({5, 6})) -> Decimal:
    """Days this request consumes from the category's balance."""
    if end < start:
        raise ValueError("The leave cannot end before it starts.")
    rule = cat.get(category)
    if half:
        if not rule.half_day:
            raise ValueError(f"{category} cannot be taken as a half day.")
        if start != end:
            raise ValueError("A half day covers a single date.")
        return Decimal("0.5") if _working(start, closed_holidays, weekend_days) else Decimal(0)
    if rule.continuous:
        return Decimal((end - start).days + 1)
    return Decimal(sum(1 for d in days_between(start, end)
                       if _working(d, closed_holidays, weekend_days)))


def _working(d: date, closed_holidays: frozenset[date], weekend_days: frozenset[int]) -> bool:
    return d.weekday() not in weekend_days and d not in closed_holidays
