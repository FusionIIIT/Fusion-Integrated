"""Leave module database query selectors."""
from __future__ import annotations

from typing import Sequence
from django.db.models import QuerySet

from modules.leave.models import HolidayCalendar, LeaveBalance, LeaveRequest
from modules.leave.domain.constants import (
    STATUS_AWAITING_DIRECTOR_SELF_SANCTION,
    STATUS_AWAITING_ESTABLISHMENT,
    STATUS_AWAITING_FINAL_SANCTION,
    STATUS_AWAITING_SUBSTITUTE,
    STATUS_AWAITING_UNIT_HEAD,
    STATUS_CANCELLATION_PENDING,
    SUBSTITUTE_PENDING,
)


def get_leave_balances(user_id: int, year: int = 2026) -> QuerySet[LeaveBalance]:
    """Retrieve all leave balances for a user and academic/calendar year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")


def get_my_leave_requests(user_id: int) -> QuerySet[LeaveRequest]:
    """Retrieve an employee's personal leave requests."""
    return LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")


def get_leave_request_detail(request_id: int, user_id: int | None = None) -> LeaveRequest | None:
    """Retrieve a single leave request by primary key, optionally scoped to applicant."""
    qs = LeaveRequest.objects.all()
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    return qs.filter(pk=request_id).first()


def get_pending_substitute_requests(user_id: int) -> QuerySet[LeaveRequest]:
    """Retrieve requests where the user has been nominated as substitute and action is pending."""
    return LeaveRequest.objects.filter(
        substitute_user_id=user_id,
        status=STATUS_AWAITING_SUBSTITUTE,
        substitute_status=SUBSTITUTE_PENDING,
    ).order_by("start_date")


def get_pending_approvals(user_id: int, active_role: str | None = None) -> QuerySet[LeaveRequest]:
    """Retrieve actionable leave applications pending approval for the reviewer's role."""
    roles = {active_role} if active_role else set()

    # Director self-sanction or authority
    if "Director" in roles:
        return LeaveRequest.objects.filter(
            status__in=[
                STATUS_AWAITING_DIRECTOR_SELF_SANCTION,
                STATUS_AWAITING_FINAL_SANCTION,
                STATUS_CANCELLATION_PENDING,
            ]
        ).order_by("created_at")

    # Dean / Registrar
    if roles & {"Dean Academic", "Registrar"}:
        return LeaveRequest.objects.filter(
            status__in=[STATUS_AWAITING_FINAL_SANCTION, STATUS_CANCELLATION_PENDING]
        ).order_by("created_at")

    # Unit Head / HOD / General reviewer
    return LeaveRequest.objects.filter(
        status__in=[
            STATUS_AWAITING_UNIT_HEAD,
            STATUS_AWAITING_ESTABLISHMENT,
            STATUS_CANCELLATION_PENDING,
        ]
    ).order_by("created_at")


def get_calendar_events(year: int = 2026) -> QuerySet[HolidayCalendar]:
    """Retrieve all calendar entries for a given year."""
    return HolidayCalendar.objects.filter(year=year).order_by("date")
