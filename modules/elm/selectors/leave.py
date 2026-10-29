"""Role scope and query functions for ELM.

Ownership filtering lives here -- once per module, not once per view.
A request outside a user's scope resolves to 404 naturally.
"""
from __future__ import annotations

import datetime
from django.db.models import QuerySet

from modules.elm.domain import state_machine as sm
from modules.elm.models import HolidayCalendar, LeaveBalance, LeaveRequest


P_VIEW_ALL = "elm.leave.view_all"
P_APPROVE = "elm.leave.approve"
P_ADMIN = "elm.admin.manage_calendar"


def visible_leave_requests(principal) -> QuerySet[LeaveRequest]:
    """Returns the base queryset of leave requests that this principal may see."""
    qs = LeaveRequest.objects.all().order_by("-created_at")
    if principal is None:
        return qs.none()

    if getattr(principal, "is_superuser", False) or principal.has_permission(P_VIEW_ALL):
        return qs

    user_id = getattr(principal, "user_id", None)
    if user_id is None:
        return qs.none()

    # Employee can see their own, plus any where they are nominated substitute
    return qs.filter(user_id=user_id)


def visible_substitute_requests(principal) -> QuerySet[LeaveRequest]:
    """Requests where this principal has been nominated as substitute."""
    if principal is None:
        return LeaveRequest.objects.none()

    user_id = getattr(principal, "user_id", None)
    if not user_id:
        return LeaveRequest.objects.none()

    return LeaveRequest.objects.filter(
        substitute_id=user_id,
        status=sm.AWAITING_SUBSTITUTE,
    ).order_by("-created_at")


def pending_approvals(principal) -> QuerySet[LeaveRequest]:
    """Requests awaiting review or sanction by this principal."""
    if principal is None:
        return LeaveRequest.objects.none()

    if getattr(principal, "is_superuser", False) or principal.has_permission(P_ADMIN):
        return LeaveRequest.objects.filter(
            status__in=[
                sm.AWAITING_UNIT_HEAD,
                sm.AWAITING_ESTABLISHMENT,
                sm.AWAITING_SANCTION,
                sm.CANCEL_REQUESTED,
                sm.EXTENSION_REQUESTED,
                sm.RESUMPTION_SUBMITTED,
            ]
        ).order_by("created_at")

    if principal.has_permission(P_APPROVE):
        # Approver queue
        return LeaveRequest.objects.filter(
            status__in=[
                sm.AWAITING_UNIT_HEAD,
                sm.AWAITING_SANCTION,
                sm.CANCEL_REQUESTED,
                sm.EXTENSION_REQUESTED,
                sm.RESUMPTION_SUBMITTED,
            ]
        ).exclude(user_id=getattr(principal, "user_id", None)).order_by("created_at")

    return LeaveRequest.objects.none()


def visible_balances(principal, user_id: int | None = None, year: int | None = None) -> QuerySet[LeaveBalance]:
    """Returns balances scoped to permission."""
    current_year = year or datetime.date.today().year
    qs = LeaveBalance.objects.filter(year=current_year)

    if principal is None:
        return qs.none()

    target_user_id = user_id or getattr(principal, "user_id", None)
    if not target_user_id:
        return qs.none()

    # Can view other's balance only if has view_all
    if target_user_id != getattr(principal, "user_id", None) and not principal.has_permission(P_VIEW_ALL):
        return qs.none()

    return qs.filter(user_id=target_user_id).order_by("category")


def published_holidays(year: int | None = None) -> QuerySet[HolidayCalendar]:
    """Published holiday calendar for a year."""
    yr = year or datetime.date.today().year
    return HolidayCalendar.objects.filter(year=yr, is_published=True).order_by("date")
