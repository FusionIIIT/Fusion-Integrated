"""Counting chargeable leave days (BR-EL-010, BR-EL-011).

    EL / COL / VL  continuous — every calendar day in the interval counts,
                   including intervening weekends and closed holidays.
    CL / SCL / RH  working days — weekends and closed holidays do not count.
    A CL half day is a flat 0.5.

Pure: takes dates and a set of closed dates, returns a Decimal.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain import enums as e


class CountingError(Exception):
    pass


def _iter_days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def chargeable_days(*, category: str, start: date, end: date,
                    half_day: str = "", closed_dates: frozenset[date] = frozenset()
                    ) -> Decimal:
    """The number of leave days this interval consumes."""
    if end < start:
        raise CountingError("The end date is before the start date.")

    if half_day:
        if category not in e.HALF_DAY:
            raise CountingError(
                f"Half days are not supported for {category} leave.")
        if start != end:
            raise CountingError(
                "A half day must start and end on the same date.")
        return Decimal("0.5")

    if category in e.CONTINUOUS:
        return Decimal((end - start).days + 1)

    count = sum(1 for d in _iter_days(start, end)
                if d.weekday() < 5 and d not in closed_dates)
    return Decimal(count)
