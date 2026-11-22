"""Read queries for holidays and vacation periods."""
from __future__ import annotations

import datetime
from django.db.models import QuerySet

from modules.leave.models import HolidayCalendar, VacationPeriod


def get_published_holidays(year: int | None = None) -> QuerySet[HolidayCalendar]:
    """Retrieve published holidays."""
    if year is None:
        year = datetime.date.today().year
    return HolidayCalendar.objects.filter(year=year, is_published=True).order_by("date")


def get_vacation_periods(year: int | None = None) -> QuerySet[VacationPeriod]:
    """Retrieve active vacation periods."""
    if year is None:
        year = datetime.date.today().year
    return VacationPeriod.objects.filter(year=year, is_active=True).order_by("start_date")
