"""Leave-day counting (BR-EL-010 half day, BR-EL-011 continuous counting)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain.errors import RuleViolation

FULL = ""
FIRST_HALF = "first_half"
SECOND_HALF = "second_half"

HALVES: tuple[str, ...] = (FIRST_HALF, SECOND_HALF)

HALF_DAY = Decimal("0.5")


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def dates_between(start: date, end: date) -> list[date]:
    """Inclusive on both ends; a single-day leave is one date."""
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def half_day_label(half: str) -> str:
    return {FIRST_HALF: "first half", SECOND_HALF: "second half"}.get(half, "")


def count_days(*, category: str, start: date, end: date, half: str = FULL,
               closed_dates: set[date] | frozenset[date] = frozenset()) -> Decimal:
    """Days this request consumes, by the category's own counting rule."""
    if end < start:
        raise RuleViolation("The leave end date is before its start date.",
                            code="period_invalid")

    if half:
        if not cat.allows_half_day(category):
            raise RuleViolation(
                f"{cat.LABELS.get(category, category)} does not support half days.",
                code="half_day_not_supported")
        if start != end:
            raise RuleViolation("A half day must start and end on the same date.",
                                code="half_day_period")
        if half not in HALVES:
            raise RuleViolation("A half day must be the first half or the second half.",
                                code="half_day_invalid")
        return HALF_DAY

    days = dates_between(start, end)
    if cat.counts_continuously(category):
        return Decimal(len(days))

    closed = set(closed_dates)
    return Decimal(len([d for d in days if not is_weekend(d) and d not in closed]))


def same_date_different_halves(*, category: str, half: str, start: date, end: date,
                               other_category: str, other_half: str,
                               other_start: date, other_end: date) -> bool:
    """BR-EL-012's single exception: two CL halves on one date do not overlap."""
    return bool(
        category == cat.CL and other_category == cat.CL
        and half and other_half
        and start == end == other_start == other_end
        and half != other_half
    )
