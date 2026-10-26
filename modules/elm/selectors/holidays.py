"""Read-only selectors for holiday calendars."""
from __future__ import annotations

from collections.abc import Set
from datetime import date
from django.db.models import QuerySet

from modules.elm.models.holidays import HolidayCalendar


def get_holidays_for_year(year: int) -> QuerySet[HolidayCalendar]:
    """Retrieve published holidays for a calendar year."""
    return HolidayCalendar.objects.filter(year=year, is_published=True).order_by("date")


def get_closed_holiday_dates(year: int) -> Set[date]:
    """Retrieve a set of closed holiday dates for a year to support working-day calculations."""
    return set(
        HolidayCalendar.objects.filter(
            year=year,
            holiday_type="closed",
            is_published=True,
        ).values_list("date", flat=True)
    )
