"""Calendar selectors for holidays and vacation periods."""

from datetime import date

from django.db.models import QuerySet

from modules.leave.models import HolidayCalendar, VacationPeriod


def list_holidays(year: int, published_only: bool = True) -> QuerySet[HolidayCalendar]:
    qs = HolidayCalendar.objects.filter(year=year).order_by("date")
    if published_only:
        qs = qs.filter(is_published=True)
    return qs


def list_vacations(year: int, published_only: bool = True) -> QuerySet[VacationPeriod]:
    qs = VacationPeriod.objects.filter(year=year).order_by("start_date")
    if published_only:
        qs = qs.filter(is_published=True)
    return qs


def get_closed_holiday_dates(year: int) -> set[date]:
    return set(
        HolidayCalendar.objects.filter(
            year=year, is_closed_holiday=True, is_published=True
        ).values_list("date", flat=True)
    )


def get_restricted_holiday_dates(year: int) -> set[date]:
    return set(
        HolidayCalendar.objects.filter(
            year=year, is_restricted_holiday=True, is_published=True
        ).values_list("date", flat=True)
    )


def get_vacation_period_tuples(year: int) -> list[tuple[date, date]]:
    return list(
        VacationPeriod.objects.filter(year=year, is_published=True).values_list(
            "start_date", "end_date"
        )
    )
