"""Calendar selectors for holidays and vacation periods.

Implements queries for BR-EL-003, BR-EL-006, BR-EL-031.
"""
from datetime import date

from modules.leave.models.calendar import HolidayCalendar, HolidayItem
from modules.leave.models.policy import VacationPeriod


def get_active_calendar(year: int) -> HolidayCalendar | None:
    """Returns the effective published holiday calendar for the given year (BR-EL-031)."""
    return HolidayCalendar.objects.filter(year=year, is_published=True).first()


def get_published_rh_dates(year: int) -> set[date]:
    """Returns set of dates configured as Restricted Holidays (BR-EL-003)."""
    cal = get_active_calendar(year)
    if not cal:
        return set()
    return set(
        HolidayItem.objects.filter(calendar=cal, is_restricted_holiday=True)
        .values_list("date", flat=True)
    )


def get_closed_holidays(year: int) -> set[date]:
    """Returns set of closed holidays (excluding RHs) for leave day counting."""
    cal = get_active_calendar(year)
    if not cal:
        return set()
    return set(
        HolidayItem.objects.filter(calendar=cal, is_restricted_holiday=False)
        .values_list("date", flat=True)
    )


def get_vacation_periods() -> list[tuple[date, date]]:
    """Returns list of active vacation periods for VL eligibility (BR-EL-006)."""
    return list(
        VacationPeriod.objects.all().values_list("start_date", "end_date")
    )
