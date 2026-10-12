"""Reading and maintaining the holiday/RH calendar (BR-EL-003/031) and vacation
periods (BR-EL-006)."""
from __future__ import annotations

from datetime import date

from django.db.models import Q
from django.utils import timezone

from modules.elm.models import Holiday, HolidayCalendar, VacationPeriod


def effective_calendar() -> HolidayCalendar | None:
    """The currently effective published calendar (most recent publication)."""
    return (HolidayCalendar.objects
            .filter(is_published=True)
            .order_by("-published_at", "-id")
            .first())


def closed_dates(calendar: HolidayCalendar | None = None) -> frozenset[date]:
    calendar = calendar or effective_calendar()
    if calendar is None:
        return frozenset()
    return frozenset(calendar.holidays.filter(kind="closed")
                     .values_list("date", flat=True))


def restricted_dates(calendar: HolidayCalendar | None = None) -> frozenset[date]:
    calendar = calendar or effective_calendar()
    if calendar is None:
        return frozenset()
    return frozenset(calendar.holidays.filter(kind="restricted")
                     .values_list("date", flat=True))


def is_restricted_holiday(day: date) -> bool:
    return day in restricted_dates()


def within_vacation(start: date, end: date) -> bool:
    """Whether [start, end] falls inside a single cached vacation period."""
    return VacationPeriod.objects.filter(
        start_date__lte=start, end_date__gte=end).exists()


def periods_overlapping(start: date, end: date):
    return VacationPeriod.objects.filter(
        Q(start_date__lte=end) & Q(end_date__gte=start))


# -- maintenance ---------------------------------------------------------------
def list_calendars():
    return HolidayCalendar.objects.all()


def create_calendar(*, name: str, year: int) -> HolidayCalendar:
    return HolidayCalendar.objects.create(name=name, year=year)


def add_holiday(*, calendar: HolidayCalendar, day: date, kind: str,
                name: str = "") -> Holiday:
    row, _ = Holiday.objects.update_or_create(
        calendar=calendar, date=day, kind=kind, defaults={"name": name})
    return row


def publish_calendar(*, calendar: HolidayCalendar,
                     actor_user_id: int | None) -> HolidayCalendar:
    calendar.is_published = True
    calendar.published_at = timezone.now()
    calendar.published_by_user_id = actor_user_id
    calendar.save(update_fields=["is_published", "published_at",
                                 "published_by_user_id", "updated_at"])
    return calendar


def holidays_for(calendar: HolidayCalendar):
    return calendar.holidays.all()


def list_vacation_periods():
    return VacationPeriod.objects.all()


def add_vacation_period(*, label: str, start: date, end: date,
                        academic_year: str = "") -> VacationPeriod:
    return VacationPeriod.objects.create(
        label=label, start_date=start, end_date=end, academic_year=academic_year)
