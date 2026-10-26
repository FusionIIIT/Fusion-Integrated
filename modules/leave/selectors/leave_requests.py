"""Selectors for Employee Leave Management (ELM).

All reads live here. Ownership filtering is enforced here at queryset level.
"""
from typing import Optional
from django.db.models import QuerySet
from modules.leave.models import (
    HolidayCalendar,
    LeaveActionLog,
    LeaveBalance,
    LeavePolicyConfig,
    LeaveRequest,
    SLAConfig,
    VacationPeriod,
)


def list_user_leave_requests(user_id: int, status: Optional[str] = None) -> QuerySet[LeaveRequest]:
    """List leave requests belonging to a user, optionally filtered by status."""
    qs = LeaveRequest.objects.filter(user_id=user_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_user_leave_request(user_id: int, request_id: int) -> LeaveRequest:
    """Get a single leave request owned by user. Raises DoesNotExist if not owned."""
    return LeaveRequest.objects.get(id=request_id, user_id=user_id)


def get_leave_request_for_review(request_id: int) -> LeaveRequest:
    """Get a leave request for authority review."""
    return LeaveRequest.objects.get(id=request_id)


def list_substitute_requests(substitute_user_id: int, pending_only: bool = False) -> QuerySet[LeaveRequest]:
    """List requests where user is nominated as substitute."""
    qs = LeaveRequest.objects.filter(substitute_user_id=substitute_user_id)
    if pending_only:
        qs = qs.filter(substitute_status="PENDING")
    return qs.order_by("-created_at")


def get_substitute_request(substitute_user_id: int, request_id: int) -> LeaveRequest:
    """Get a specific substitute request for the nominated substitute."""
    return LeaveRequest.objects.get(id=request_id, substitute_user_id=substitute_user_id)


def list_approvals_inbox(status: Optional[str] = None) -> QuerySet[LeaveRequest]:
    """List requests pending review or sanction."""
    qs = LeaveRequest.objects.filter(
        status__in=["PENDING_UNIT_HEAD", "PENDING_SANCTION", "CANCEL_REQUESTED", "RESUMED"]
    )
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Get all leave category balances for an employee in a given year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")


def get_holiday_calendar(year: int) -> QuerySet[HolidayCalendar]:
    """Get published holiday calendar for a year."""
    return HolidayCalendar.objects.filter(year=year, published=True).order_by("date")


def get_vacation_periods(year: int) -> QuerySet[VacationPeriod]:
    """Get vacation periods for a year."""
    return VacationPeriod.objects.filter(year=year).order_by("start_date")


def get_audit_trail(leave_request_id: int) -> QuerySet[LeaveActionLog]:
    """Get historical action log for a leave request."""
    return LeaveActionLog.objects.filter(leave_request_id=leave_request_id).order_by("created_at")


def get_active_leaves_for_user(user_id: int) -> list[dict]:
    """Get active/pending leave intervals for an employee for overlap checking."""
    leaves = LeaveRequest.objects.filter(user_id=user_id).exclude(
        status__in=["REJECTED", "WITHDRAWN", "CANCELLED"]
    ).values("start_date", "end_date", "category", "half_day", "status")
    return list(leaves)
