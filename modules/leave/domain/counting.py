"""How many days a request consumes, and when two requests collide."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from modules.leave.domain.categories import CONTINUOUS_COUNT, Category


class Half(StrEnum):
    FULL = "full"
    FIRST = "first"
    SECOND = "second"


class InvalidPeriod(ValueError):
    pass


def _dates(start: date, end: date) -> Iterable[date]:
    for i in range((end - start).days + 1):
        yield start + timedelta(days=i)


def leave_days(category: Category, start: date, end: date, half: Half,
               closed_holidays: set[date]) -> Decimal:
    if end < start:
        raise InvalidPeriod("The leave cannot end before it starts.")
    if half is not Half.FULL:
        # BR-EL-010: only CL has halves, and a half is always a single date.
        if category is not Category.CL:
            raise InvalidPeriod("Half-day leave is available for Casual Leave only.")
        if start != end:
            raise InvalidPeriod("A half-day leave must start and end on the same date.")
        return Decimal("0.5")
    if category in CONTINUOUS_COUNT:
        return Decimal((end - start).days + 1)
    working = sum(1 for d in _dates(start, end)
                  if d.weekday() < 5 and d not in closed_holidays)
    if not working:
        raise InvalidPeriod(
            "Every date in this period is a weekend or a closed holiday; "
            "no leave is needed for it.")
    return Decimal(working)


@dataclass(frozen=True)
class Interval:
    start: date
    end: date
    half: Half = Half.FULL


def overlaps(a: Interval, b: Interval) -> bool:
    """BR-EL-012: different CL halves of the same date do not collide."""
    if a.end < b.start or b.end < a.start:
        return False
    same_day = a.start == a.end == b.start == b.end
    return not (same_day and Half.FULL not in (a.half, b.half) and a.half != b.half)


def dates_in(start: date, end: date) -> list[date]:
    return list(_dates(start, end))
