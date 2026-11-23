"""Deadline arithmetic: business days for review, calendar days for revision and appeal."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

REVIEW_BUSINESS_DAYS = 15   # BR-PMS-031
REVISION_DAYS = 60          # BR-PMS-035


def is_business_day(day: date, holidays: Iterable[date]) -> bool:
    return day.weekday() < 5 and day not in set(holidays)


def add_business_days(start: date, days: int, holidays: Iterable[date]) -> date:
    """The date `days` business days after `start`, skipping weekends and holidays."""
    if days < 0:
        raise ValueError("days must not be negative")
    off = frozenset(holidays)
    current, counted = start, 0
    while counted < days:
        current += timedelta(days=1)
        if is_business_day(current, off):
            counted += 1
    return current


def review_due(assigned_on: date, holidays: Iterable[date]) -> date:
    return add_business_days(assigned_on, REVIEW_BUSINESS_DAYS, holidays)


def revision_due(decided_on: date) -> date:
    return decided_on + timedelta(days=REVISION_DAYS)


def appeal_due(rejected_on: date, period_days: int) -> date:
    return rejected_on + timedelta(days=period_days)


def on_or_before(today: date, deadline: date | None) -> bool:
    return deadline is None or today <= deadline
