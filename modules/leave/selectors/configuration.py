"""Reads of calendars, vacation periods and year-end runs."""
from __future__ import annotations

from modules.leave.models import HolidayCalendar, VacationPeriod, YearEndRun


def published_calendar(year: int) -> HolidayCalendar | None:
    return (HolidayCalendar.objects.filter(year=year, status=HolidayCalendar.PUBLISHED)
            .prefetch_related("holidays").first())


def calendars(year: int):
    return (HolidayCalendar.objects.filter(year=year).prefetch_related("holidays")
            .order_by("-version"))


def vacations(year: int | None = None):
    qs = VacationPeriod.objects.all()
    if year is not None:
        qs = qs.filter(start_date__year__lte=year, end_date__year__gte=year)
    return qs.order_by("start_date")


def year_end_runs():
    return YearEndRun.objects.order_by("-year")
