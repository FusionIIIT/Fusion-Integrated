"""Leave selectors — all reads go through here."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.leave.models import LeaveBalance, LeaveRequest, LeaveType


def leave_types_active() -> QuerySet[LeaveType]:
    return LeaveType.objects.filter(is_active=True).order_by("code")


def leave_type_by_id(type_id: int) -> LeaveType | None:
    return LeaveType.objects.filter(pk=type_id, is_active=True).first()


def balance_for_user_and_type(user_id: int, type_id: int, year: int) -> LeaveBalance | None:
    return (
        LeaveBalance.objects
        .filter(user_id=user_id, leave_type_id=type_id, year=year)
        .first()
    )


def balances_for_user(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    return (
        LeaveBalance.objects
        .filter(user_id=user_id, year=year)
        .select_related("leave_type")
        .order_by("leave_type__code")
    )


def requests_for_user(user_id: int) -> QuerySet[LeaveRequest]:
    return (
        LeaveRequest.objects
        .filter(user_id=user_id)
        .select_related("leave_type")
        .order_by("-created_at")
    )


def pending_requests() -> QuerySet[LeaveRequest]:
    return (
        LeaveRequest.objects
        .filter(status="pending")
        .select_related("leave_type")
        .order_by("start_date")
    )
