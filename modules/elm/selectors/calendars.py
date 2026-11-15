"""Calendar selectors for ELM."""
from __future__ import annotations

from datetime import date

from modules.elm.models import Holiday, HolidayCalendar, VacationPeriod


def get_published_calendar(year: int) -> HolidayCalendar | None:
    """Return published holiday calendar for a year (BR-EL-031)."""
    return HolidayCalendar.objects.filter(year=year, is_published=True).first()


def get_closed_holidays_set(year: int) -> set[date]:
    """Return set of closed holiday dates from the published calendar."""
    cal = get_published_calendar(year)
    if not cal:
        return set()
    return set(
        Holiday.objects.filter(
            calendar=cal, holiday_type="closed_holiday"
        ).values_list("date", flat=True)
    )


def get_restricted_holidays_set(year: int) -> set[date]:
    """Return set of restricted holiday dates from the published calendar."""
    cal = get_published_calendar(year)
    if not cal:
        return set()
    return set(
        Holiday.objects.filter(
            calendar=cal, holiday_type="restricted_holiday"
        ).values_list("date", flat=True)
    )


def get_active_vacation_periods(academic_year: str | None = None) -> list[VacationPeriod]:
    """Return active academic calendar vacation periods."""
    qs = VacationPeriod.objects.filter(is_active=True)
    if academic_year:
        qs = qs.filter(academic_year=academic_year)
    return list(qs.order_by("start_date"))
