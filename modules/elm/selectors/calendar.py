"""Holiday calendar and vacation period selectors (BR-EL-003, BR-EL-006, BR-EL-031)."""
from __future__ import annotations

import datetime
from django.db.models import QuerySet

from modules.elm.domain.eligibility import VacationPeriod
from modules.elm.models import AcademicVacationPeriod, HolidayCalendar


def get_published_holidays(year: int) -> QuerySet[HolidayCalendar]:
    """Retrieve published holidays for the year."""
    return HolidayCalendar.objects.filter(year=year, is_published=True).order_by("date")


def get_published_rh_dates(year: int) -> set[datetime.date]:
    """Retrieve set of published Restricted Holiday dates for the year (BR-EL-003, BR-EL-031)."""
    return set(
        HolidayCalendar.objects.filter(
            year=year,
            is_restricted_holiday=True,
            is_published=True,
        ).values_list("date", flat=True)
    )


def get_closed_holiday_dates(year: int) -> set[datetime.date]:
    """Retrieve set of closed holiday dates for the year (for counting exclusions)."""
    return set(
        HolidayCalendar.objects.filter(
            year=year,
            is_closed_holiday=True,
            is_published=True,
        ).values_list("date", flat=True)
    )


def get_academic_vacation_periods(year: int) -> list[VacationPeriod]:
    """Retrieve active vacation periods from Academic Calendar (EXT-01, BR-EL-006)."""
    rows = AcademicVacationPeriod.objects.filter(year=year, is_active=True).order_by("start_date")
    return [
        VacationPeriod(name=r.name, start_date=r.start_date, end_date=r.end_date)
        for r in rows
    ]
