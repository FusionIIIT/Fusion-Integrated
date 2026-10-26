"""Read selectors for Leave Balances, Holiday Calendars, and Vacation Periods."""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.db.models import QuerySet

from modules.elm.models import HolidayCalendar, LeaveBalance, VacationPeriod


def get_user_balances(user_id: int, year: int = 2026) -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("leave_category")


def get_user_category_balance(user_id: int, category: str, year: int = 2026) -> Decimal:
    try:
        bal = LeaveBalance.objects.get(user_id=user_id, leave_category=category, year=year)
    except LeaveBalance.DoesNotExist:
        return Decimal("0.0")
    else:
        return bal.available


def get_published_rh_dates(year: int = 2026) -> set[datetime.date]:
    return set(
        HolidayCalendar.objects.filter(year=year, is_rh=True, is_published=True).values_list(
            "date", flat=True
        )
    )


def get_closed_holiday_dates(year: int = 2026) -> set[datetime.date]:
    return set(
        HolidayCalendar.objects.filter(year=year, is_closed=True, is_published=True).values_list(
            "date", flat=True
        )
    )


def get_vacation_periods(year: int = 2026) -> list[tuple[datetime.date, datetime.date]]:
    periods = VacationPeriod.objects.filter(year=year).values_list("start_date", "end_date")
    return list(periods)
