"""Chargeable-day counting (BR-EL-010, BR-EL-011, CFR-EL-010, CFR-EL-003.3).

Pure functions over dates. The closed-holiday set is injected rather than
looked up, so the rule is testable without a calendar row and the service
remains the only place that knows where holidays come from.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain.categories import (
    CONTINUOUS_CATEGORIES,
    HALF_FIRST,
    HALF_SECOND,
    is_continuous,
)

DAY = Decimal("1")
HALF = Decimal("0.5")


class CountingError(ValueError):
    """The interval itself is malformed (end before start)."""


def daterange(start: date, end: date) -> list[date]:
    if end < start:
        raise CountingError("end date is before start date")
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def chargeable_days(
    *,
    category: str,
    start: date,
    end: date,
    half_day: str = "none",
    closed_holidays: frozenset[date] | set[date] = frozenset(),
) -> Decimal:
    """Days this request consumes, per the category's counting rule.

    For EL, COL and VL every day in the interval counts — weekends and closed
    holidays inside a continuous absence are still absence (BR-EL-011). For
    CL, SCL and RH only days that are neither a weekend nor a closed holiday
    count. A half-day CL on a single date is exactly 0.5 (BR-EL-010);
    a half-day value on a multi-day CL interval is a caller error.
    """
    if category in CONTINUOUS_CATEGORIES:
        span = Decimal(len(daterange(start, end)))
        return span

    days = Decimal(0)
    for d in daterange(start, end):
        if d.weekday() >= 5 or d in closed_holidays:
            continue
        days += DAY

    if half_day in (HALF_FIRST, HALF_SECOND):
        # A half-day request spans one date. 0.5 only if that date counts at
        # all — a half-day CL on a closed holiday consumes nothing.
        return HALF if days >= 1 else Decimal(0)
    return days


def is_continuous_category(category: str) -> bool:
    return is_continuous(category)
