"""Reads. Every query a service or view needs lives here (layering: api > services > selectors)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Q, QuerySet, Sum

from modules.elm.domain import leave_types as lt
from modules.elm.domain import workflow as wf
from modules.elm.domain.calculation import Period
from modules.elm.models import (
    ClosedHoliday,
    LeaveApplication,
    LeaveBalance,
    LeaveNotification,
    RestrictedHoliday,
    VacationPeriod,
)

ZERO = Decimal(0)


def closed_days(start: date, end: date) -> frozenset[date]:
    return frozenset(ClosedHoliday.objects.filter(
        is_published=True, date__range=(start, end)).values_list("date", flat=True))


def published_restricted_holidays(year: int) -> frozenset[date]:
    return frozenset(RestrictedHoliday.objects.filter(
        is_published=True, year=year).values_list("date", flat=True))


def vacation_periods(start: date, end: date) -> list[tuple[date, date]]:
    return list(VacationPeriod.objects.filter(
        is_published=True, start_date__lte=end, end_date__gte=start,
    ).values_list("start_date", "end_date"))


def active_periods(user_id: int, exclude_id: int | None = None) -> list[Period]:
    rows = LeaveApplication.objects.filter(user_id=user_id, status__in=wf.ACTIVE)
    if exclude_id:
        rows = rows.exclude(pk=exclude_id)
    return [Period(r.start_date, r.end_date, r.half_day) for r in rows]


def has_overlap(user_id: int, start: date, end: date) -> bool:
    """Used for substitutes: any pending or approved leave touching the period."""
    return LeaveApplication.objects.filter(
        user_id=user_id, status__in=wf.ACTIVE,
        start_date__lte=end, end_date__gte=start).exists()


def pending_days(user_id: int, year: int, leave_type: str,
                 exclude_id: int | None = None) -> Decimal:
    """Days asked for but not yet deducted. A cancellation request has already been charged."""
    rows = LeaveApplication.objects.filter(
        user_id=user_id, leave_type=leave_type, status__in=wf.PENDING,
        pending_action="", start_date__year=year)
    if exclude_id:
        rows = rows.exclude(pk=exclude_id)
    return rows.aggregate(total=Sum("days"))["total"] or ZERO


def scl_days_held(user_id: int, year: int, exclude_id: int | None = None) -> Decimal:
    rows = LeaveApplication.objects.filter(
        user_id=user_id, leave_type=lt.SCL, status__in=wf.ACTIVE, start_date__year=year)
    if exclude_id:
        rows = rows.exclude(pk=exclude_id)
    return rows.aggregate(total=Sum("days"))["total"] or ZERO


def balance(user_id: int, year: int, leave_type: str, *, lock: bool = False):
    rows = LeaveBalance.objects.filter(user_id=user_id, year=year, leave_type=leave_type)
    return (rows.select_for_update() if lock else rows).first()


def balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("leave_type")


def application(pk: int, *, lock: bool = False) -> LeaveApplication | None:
    rows = LeaveApplication.objects.filter(pk=pk)
    return (rows.select_for_update() if lock else rows).first()


def own_applications(user_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at", "-id")


def involves(user_id: int) -> QuerySet[LeaveApplication]:
    """Mine, or I am the nominated substitute."""
    return LeaveApplication.objects.filter(
        Q(user_id=user_id) | Q(substitute_user_id=user_id))


def live_extensions(application_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(extends_id=application_id, status__in=wf.ACTIVE)


def notifications_for(user_id: int, permissions: frozenset[str]) -> QuerySet[LeaveNotification]:
    return LeaveNotification.objects.filter(
        Q(recipient_user_id=user_id) | Q(recipient_permission__in=permissions))


def applications_awaiting(status: str) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(status=status).order_by("waiting_since")


def calendar() -> dict[str, list[dict]]:
    return {
        "restricted_holidays": list(RestrictedHoliday.objects.filter(
            is_published=True).order_by("date").values("date", "name", "year")),
        "closed_holidays": list(ClosedHoliday.objects.filter(
            is_published=True).order_by("date").values("date", "name")),
        "vacation_periods": list(VacationPeriod.objects.filter(
            is_published=True).order_by("start_date").values("name", "start_date", "end_date")),
    }
