"""Row-level scoping for ELM queries.

Adheres to Fusion architecture: visibility is determined by narrowing querysets
so unpermitted rows 404 rather than 403.
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType


def scope_leave_requests(principal) -> QuerySet:
    if principal is None:
        return LeaveRequest.objects.none()
    if principal.has_permission("elm.leave_request.view") or principal.has_permission(
        "elm.leave_request.review"
    ):
        return LeaveRequest.objects.select_related("leave_type").all()
    return LeaveRequest.objects.filter(
        employee_user_id=principal.user_id
    ).select_related("leave_type")


def scope_leave_balances(principal) -> QuerySet:
    if principal is None:
        return LeaveBalance.objects.none()
    if principal.has_permission("elm.leave_balance.view"):
        return LeaveBalance.objects.select_related("leave_type").all()
    return LeaveBalance.objects.filter(user_id=principal.user_id).select_related(
        "leave_type"
    )


def scope_leave_types(principal) -> QuerySet:
    if principal is None:
        return LeaveType.objects.none()
    return LeaveType.objects.all()
