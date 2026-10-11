"""Balances and calendars, read-only."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Sum

from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm
from modules.elm.models import (
    Holiday,
    HolidayCalendar,
    LeaveRequest,
    LedgerEntry,
    VacationPeriod,
)

ZERO = Decimal("0")


def balances(user_id: int, year: int) -> dict[str, Decimal]:
    rows = (LedgerEntry.objects.filter(user_id=user_id, year=year)
            .values("category").annotate(total=Sum("days")))
    out = dict.fromkeys(policy.CATEGORIES, ZERO)
    for r in rows:
        out[r["category"]] = r["total"] or ZERO
    return out


def ledger_entries(user_id: int, year: int):
    return LedgerEntry.objects.filter(user_id=user_id, year=year)


def reserved(user_id: int, category: str, exclude_id: int | None = None) -> Decimal:
    """Days asked for in still-pending requests, so two can't spend one balance."""
    qs = LeaveRequest.objects.filter(
        user_id=user_id, category=category, state__in=sm.PENDING,
        kind__in=(LeaveRequest.LEAVE, LeaveRequest.EXTENSION))
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.aggregate(t=Sum("days"))["t"] or ZERO


def published_calendar(year: int) -> HolidayCalendar | None:
    """BR-EL-031: the latest published calendar stays in force until replaced."""
    return (HolidayCalendar.objects
            .filter(year=year, status=HolidayCalendar.PUBLISHED)
            .order_by("-published_at", "-id").first())


def holiday_dates(start: date, end: date, kind: str) -> set[date]:
    out: set[date] = set()
    for year in range(start.year, end.year + 1):
        cal = published_calendar(year)
        if cal is not None:
            out |= set(Holiday.objects.filter(calendar=cal, kind=kind,
                                              date__range=(start, end))
                       .values_list("date", flat=True))
    return out


def vacation_periods() -> list[tuple[date, date]]:
    return list(VacationPeriod.objects.values_list("start_date", "end_date"))


def active_intervals(user_id: int, exclude_id: int | None = None
                     ) -> list[policy.Interval]:
    """BR-EL-012 / BR-EL-014: pending or approved leave and extensions."""
    qs = LeaveRequest.objects.filter(
        user_id=user_id, kind__in=(LeaveRequest.LEAVE, LeaveRequest.EXTENSION),
        state__in=sm.PENDING | {sm.APPROVED})
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return [policy.Interval(r.start_date, r.end_date, r.half or None)
            for r in qs.only("start_date", "end_date", "half")]


def effective_end(leave: LeaveRequest) -> date:
    """The approved end, pushed out by any approved extension (BR-EL-025)."""
    ext = (leave.children.filter(kind=LeaveRequest.EXTENSION, state=sm.APPROVED)
           .order_by("-end_date").values_list("end_date", flat=True).first())
    return max(leave.end_date, ext) if ext else leave.end_date
