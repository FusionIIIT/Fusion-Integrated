"""Reads over the leave account, the calendar and the ledger.

Like every selector here these narrow; they never decide.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from modules.leave.models import CalendarEntry, LeaveBalance, LeaveCalendar


def balances(user_id: int, year_label: str):
    return (LeaveBalance.objects
            .filter(user_id=user_id, year_label=year_label)
            .order_by("category"))


def balance_for(user_id: int, year_label: str, category: str) -> Decimal:
    """Available days, or zero for a category the employee has no account for."""
    row = LeaveBalance.objects.filter(user_id=user_id, year_label=year_label,
                                      category=category).first()
    return row.available if row else Decimal(0)


def published_calendar(year_label: str):
    """The calendar that governs date and RH validation right now (BR-EL-031).

    A draft is invisible here: until a replacement is published, the one in
    force stays in force.
    """
    return (LeaveCalendar.objects
            .filter(year_label=year_label, published_at__isnull=False)
            .order_by("-published_at")
            .first())


def closed_dates(calendar) -> frozenset[date]:
    if calendar is None:
        return frozenset()
    return frozenset(CalendarEntry.objects
                     .filter(calendar=calendar, kind="closed_holiday")
                     .values_list("date", flat=True))


def restricted_holidays(calendar) -> frozenset[date]:
    if calendar is None:
        return frozenset()
    return frozenset(CalendarEntry.objects
                     .filter(calendar=calendar, kind="restricted_holiday")
                     .values_list("date", flat=True))


def vacation_periods(calendar) -> tuple[tuple[date, date], ...]:
    """Vacation periods projected from the Academic Calendar (EXT-01)."""
    if calendar is None:
        return ()
    rows = (CalendarEntry.objects
            .filter(calendar=calendar, kind="vacation")
            .order_by("date"))
    return tuple((r.date, r.ends_on or r.date) for r in rows)


def effective_calendar(year_label: str):
    """The published calendar plus everything a validation run needs."""
    cal = published_calendar(year_label)
    return {
        "calendar": cal,
        "closed_dates": closed_dates(cal),
        "restricted_holidays": restricted_holidays(cal),
        "vacation_periods": vacation_periods(cal),
    }
