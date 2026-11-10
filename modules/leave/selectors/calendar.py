"""BR-EL-031: only the published calendar counts; BR-EL-006 vacation periods."""
from __future__ import annotations

from datetime import date

from modules.leave.models import Holiday, HolidayCalendar, VacationPeriod


def published(year: int) -> HolidayCalendar | None:
    return (HolidayCalendar.objects.filter(year=year, status=HolidayCalendar.PUBLISHED)
            .prefetch_related("holidays").first())


def holidays(year: int, kind: str) -> set[date] | None:
    """None when nothing is published for the year, which callers must refuse on."""
    cal = published(year)
    if cal is None:
        return None
    return {h.date for h in Holiday.objects.filter(calendar=cal, kind=kind)}


def within_vacation(start: date, end: date) -> bool:
    return VacationPeriod.objects.filter(start_date__lte=start, end_date__gte=end).exists()
