"""How many leave days an interval consumes (ELM Problem Statement §4).

EL/COL/VL count continuously: every calendar day in the interval, weekends and
closed holidays included. CL/SCL/RH do not — they count working days only, so a
weekend inside a CL interval costs nothing.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from .categories import LeaveCategory


class InvalidLeavePeriod(ValueError):
    pass


def _each_day(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def count_leave_days(
    *,
    category: LeaveCategory,
    starts_on: date,
    ends_on: date,
    closed_holidays: frozenset[date] = frozenset(),
    half_day: str = "none",
) -> Decimal:
    """Days consumed by one application.

    `half_day` is one of none/first_half/second_half and is only meaningful for
    CL; a half day consumes 0.5 of the day it sits on.
    """
    if ends_on < starts_on:
        raise InvalidLeavePeriod("The leave period ends before it starts.")

    days = list(_each_day(starts_on, ends_on))

    if category in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
        total = Decimal(len(days))
    else:
        total = Decimal(sum(1 for d in days if not is_weekend(d)
                            and d not in closed_holidays))

    if half_day and half_day != "none":
        if category is not LeaveCategory.CL:
            raise InvalidLeavePeriod("Half days are only supported for CL.")
        if starts_on != ends_on:
            raise InvalidLeavePeriod("A half day must be a single date.")
        if starts_on in closed_holidays or is_weekend(starts_on):
            raise InvalidLeavePeriod("A half day cannot fall on a holiday.")
        total = Decimal("0.5")

    if total <= 0:
        raise InvalidLeavePeriod(
            "The requested period consumes no payable leave days.")
    return total


def half_day_overlaps(a_half: str, b_half: str) -> bool:
    """First-half and second-half CL on the same date do NOT overlap (§5)."""
    if not a_half or not b_half or a_half == "none" or b_half == "none":
        return True
    return a_half == b_half
