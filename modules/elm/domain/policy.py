"""Pure leave-policy calculations. This module deliberately has no Django imports."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")
CONTINUOUS_CATEGORIES = frozenset({"EL", "COL", "VL"})


def inclusive_days(start: date, end: date) -> int:
    if end < start:
        raise ValueError("End date is before start date.")
    return (end - start).days + 1


def overlaps(
    *,
    first_start: date,
    first_end: date,
    first_half: str,
    second_start: date,
    second_end: date,
    second_half: str,
    first_category: str,
    second_category: str,
) -> bool:
    if first_start > second_end or second_start > first_end:
        return False
    return not (
        first_start == first_end == second_start == second_end
        and first_category == second_category == "CL"
        and first_half in {"first", "second"}
        and second_half in {"first", "second"}
        and first_half != second_half
    )


def chargeable_days(
    *,
    category: str,
    start: date,
    end: date,
    half_day: str = "",
    counting_rule: str = "",
    closed_dates: Iterable[date] = (),
    restricted_dates: Iterable[date] = (),
) -> Decimal:
    """Return policy days. Non-continuous counting comes from current policy."""
    if category not in CATEGORIES:
        raise ValueError("Unsupported leave category.")
    if end < start:
        raise ValueError("End date is before start date.")
    if half_day:
        if category != "CL" or start != end or half_day not in {"first", "second"}:
            raise ValueError("Only a single-day CL request can be a half day.")
        if counting_rule == "calendar_days":
            return Decimal("0.5")
        if counting_rule != "working_days":
            raise ValueError("A current leave-day counting rule is not configured.")
        if start.weekday() >= 5 or start in set(closed_dates):
            return Decimal("0")
        return Decimal("0.5")
    if category == "RH":
        days = {start + timedelta(days=n) for n in range(inclusive_days(start, end))}
        selected = days & set(restricted_dates)
        if selected != days:
            raise ValueError("Every RH date must be in the effective published RH calendar.")
        return Decimal(len(days))
    if category in CONTINUOUS_CATEGORIES or counting_rule == "continuous":
        return Decimal(inclusive_days(start, end))
    if counting_rule not in {"working_days", "calendar_days"}:
        raise ValueError("A current leave-day counting rule is not configured.")
    if counting_rule == "calendar_days":
        return Decimal(inclusive_days(start, end))
    closed = set(closed_dates)
    count = sum(
        1
        for offset in range(inclusive_days(start, end))
        if (start + timedelta(days=offset)).weekday() < 5
        and (start + timedelta(days=offset)) not in closed
    )
    return Decimal(count)


def split_days_by_year(
    *,
    category: str,
    start: date,
    end: date,
    half_day: str = "",
    counting_rule: str = "",
    closed_dates: Iterable[date] = (),
    restricted_dates: Iterable[date] = (),
) -> dict[int, Decimal]:
    """Split chargeable days at calendar-year boundaries for annual accounts."""
    if end < start:
        raise ValueError("End date is before start date.")
    closed = set(closed_dates)
    restricted = set(restricted_dates)
    result: dict[int, Decimal] = defaultdict(Decimal)
    cursor = start
    while cursor <= end:
        boundary = min(end, date(cursor.year, 12, 31))
        amount = chargeable_days(
            category=category,
            start=cursor,
            end=boundary,
            half_day=half_day if cursor == start == end else "",
            counting_rule=counting_rule,
            closed_dates=closed,
            restricted_dates=restricted,
        )
        result[cursor.year] += amount
        cursor = boundary + timedelta(days=1)
    return dict(result)
