"""Database read selectors for Employee Leave Management (ELM).

Ownership and scope filtering lives here (ADR-0010, Module Authoring Guide).
"""
from datetime import date
from django.db.models import QuerySet

from ..models import ApprovalStep, HolidayCalendarEntry, LeaveApplication, LeaveBalance, LeavePolicy


def get_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Return all active leave balances for a specific user and calendar year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")


def get_user_applications(user_id: int) -> QuerySet[LeaveApplication]:
    """Return all leave applications filed by the user."""
    return (
        LeaveApplication.objects.filter(user_id=user_id)
        .prefetch_related("approval_steps")
        .order_by("-created_at")
    )


def get_application_detail(application_id: int, user_id: int | None = None) -> LeaveApplication | None:
    """Fetch application detail. If user_id provided, ensures applicant or assignee access."""
    qs = LeaveApplication.objects.prefetch_related("approval_steps", "balance_transactions")
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    return qs.filter(pk=application_id).first()


def get_pending_approval_steps(approver_user_id: int) -> QuerySet[ApprovalStep]:
    """Return actionable approval steps currently waiting for this approver's action."""
    return (
        ApprovalStep.objects.filter(
            assigned_user_id=approver_user_id,
            decision="pending",
            application__status__in=["submitted", "recommended", "not_recommended"],
        )
        .select_related("application")
        .order_by("step_order", "-created_at")
    )


def get_pending_substitute_requests(substitute_user_id: int) -> QuerySet[LeaveApplication]:
    """Return applications waiting for this substitute's consent."""
    return LeaveApplication.objects.filter(
        substitute_user_id=substitute_user_id,
        substitute_status="pending",
        status="submitted",
    ).order_by("-created_at")


def get_holiday_calendar(year: int) -> QuerySet[HolidayCalendarEntry]:
    """Return the published holiday and RH calendar entries for a given year."""
    return HolidayCalendarEntry.objects.filter(year=year).order_by("date")


def get_leave_policies() -> QuerySet[LeavePolicy]:
    """Return configured leave policies."""
    return LeavePolicy.objects.all().order_by("category")
