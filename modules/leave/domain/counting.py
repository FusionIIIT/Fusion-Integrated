"""Half-day CL and continuous-day counting (BR-EL-010, BR-EL-011).

Whether a given date is closed (weekend or published holiday) is not decided
here: the caller supplies the predicate, because ownership of the holiday, RH
and Academic calendars is an open item in the unresolved register.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from modules.leave.domain.entitlement import CL, COL, EL, VL


class Half(StrEnum):
    """BR-EL-010 - the two halves that make up a CL day."""

    FIRST = "first_half"
    SECOND = "second_half"


HALVES: tuple[Half, ...] = (Half.FIRST, Half.SECOND)

#: BR-EL-010 - an approved half day consumes half of one CL day.
HALF_DAY_CHARGE = Decimal("0.5")

#: BR-EL-011 - intervening weekends and closed holidays are charged as leave.
CONTINUOUS_CATEGORIES: frozenset[str] = frozenset({EL, COL, VL})


def supports_half_day(category: str) -> bool:
    """BR-EL-010 - only CL is split into halves in this baseline."""
    return category == CL


def half_day_charge(*, approved: bool) -> Decimal:
    """BR-EL-010 - the deduction a half-day CL request makes once approved."""
    return HALF_DAY_CHARGE if approved else Decimal("0")


def charges_closed_days(category: str) -> bool:
    """BR-EL-011 - true for EL/COL/VL, which span an interval continuously."""
    return category in CONTINUOUS_CATEGORIES


def day_span(start: date, end: date) -> int:
    """Inclusive count of calendar days from ``start`` through ``end``."""
    if end < start:
        raise ValueError("end date precedes start date")
    return (end - start).days + 1


def counted_days(
    category: str,
    start: date,
    end: date,
    *,
    is_closed_day: Callable[[date], bool],
) -> Decimal:
    """BR-EL-011 - leave days charged for an approved interval.

    EL/COL/VL charge every calendar day in the interval, so weekends and closed
    holidays inside it count (``is_closed_day`` is not consulted). CL, SCL and
    RH charge only the days that are not closed.
    """
    if end < start:
        raise ValueError("end date precedes start date")
    if charges_closed_days(category):
        return Decimal(day_span(start, end))
    open_days = 0
    current = start
    while current <= end:
        if not is_closed_day(current):
            open_days += 1
        current += timedelta(days=1)
    return Decimal(open_days)
