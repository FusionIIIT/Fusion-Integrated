"""The calendar a request is counted against.

Validation reads the currently effective published calendar, so replacing the
calendar never changes the meaning of leave already approved under the old one
(BR-EL-031). All lookups take an explicit date range and return plain sets, so
the counting rules stay testable without a database.
"""
from __future__ import annotations

from datetime import date

from django.db.models import Q

from modules.leave.models import Holiday, HolidayCalendar, VacationPeriod
from modules.leave.models.calendar import PUBLISHED


def effective_calendar(*, year: int | None = None) -> HolidayCalendar | None:
    qs = HolidayCalendar.objects.filter(is_effective=True, status=PUBLISHED)
    if year is not None:
        qs = qs.filter(year=year)
    return qs.order_by("-year").first()


def _in_range(start: date, end: date):
    return Q(date__gte=start, date__lte=end)


def closed_holiday_dates(start: date, end: date, *,
                         calendar: HolidayCalendar | None = None) -> set[date]:
    """Every closed holiday, which is what EL/COL/VL days are counted against."""
    cal = calendar or effective_calendar()
    if cal is None:
        return set()
    return set(Holiday.objects.filter(
        calendar=cal, is_restricted_holiday=False,
        **_in_range(start, end)).values_list("date", flat=True))


def restricted_holiday_dates(start: date, end: date, *,
                             calendar: HolidayCalendar | None = None) -> set[date]:
    """Restricted Holiday days are specific to the claimant, so the caller
    filters these by the unit's applicable RH list (BR-EL-006)."""
    cal = calendar or effective_calendar()
    if cal is None:
        return set()
    return set(Holiday.objects.filter(
        calendar=cal, is_restricted_holiday=True,
        **_in_range(start, end)).values_list("date", flat=True))


def vacation_periods(start: date, end: date) -> list[VacationPeriod]:
    """EXT-01 stand-in: periods that Vacation Leave may be taken in."""
    return list(VacationPeriod.objects.filter(
        Q(end_date__gte=start), Q(start_date__lte=end)).order_by("start_date"))


def within_vacation_period(day: date) -> VacationPeriod | None:
    return VacationPeriod.objects.filter(
        start_date__lte=day, end_date__gte=day).order_by("start_date").first()