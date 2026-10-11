"""Calendar selectors for holidays and vacation periods."""

from __future__ import annotations

import datetime

from modules.leave.models import Calendar, Holiday, VacationPeriod


def get_active_calendar(year: int) -> Calendar | None:
    """Returns published calendar for the year under BR-EL-031."""
    return Calendar.objects.filter(year=year, published=True).order_by("-pk").first()


def get_calendar_holidays(calendar: Calendar) -> set[datetime.date]:
    """Returns set of closed holiday dates."""
    return set(
        Holiday.objects.filter(calendar=calendar, restricted=False).values_list("day", flat=True)
    )


def get_restricted_holidays(calendar: Calendar) -> list[datetime.date]:
    """Returns list of restricted holiday dates."""
    return list(
        Holiday.objects.filter(calendar=calendar, restricted=True).values_list("day", flat=True)
    )


def get_vacation_ranges(calendar: Calendar) -> list[tuple[datetime.date, datetime.date]]:
    """Returns list of (start, end) tuples for academic vacation periods."""
    return list(
        VacationPeriod.objects.filter(calendar=calendar).values_list("starts_on", "ends_on")
    )
