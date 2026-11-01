"""ELM selectors — read-only queries for leave data."""from __future__ import annotations

from collections.abc import Iterable, Sequence

from modules.elm.models import (
    LeaveCategory,
    EmployeeLeaveBalance,
    LeaveApplication,
    SubstituteNomination,
)


def get_leave_categories() -> Sequence[LeaveCategory]:
    """Return all configured leave categories."""
    return list(LeaveCategory.objects.all())


def get_employee_balance(user_id: int,
                        leave_category_codes: Sequence[str] | None = None) -> dict[int, EmployeeLeaveBalance]:
    """Retrieve leave balance(ves) for a user, optionally filtered by category codes."""
    from django.db.models import Q

    qs = EmployeeLeaveBalance.objects.filter(user_id=user_id)
    if leave_category_codes:
        qs = qs.filter(leave_category__code__in=leave_category_codes)
    return {b.leave_category.code: b for b in qs}


def get_pending_applications(user_id: int) -> list[LeaveApplication]:
    """Return pending leave applications for a user."""
    return list(LeaveApplication.objects.filter(
        user_id=user_id,
        status="submitted",
    ).order_by("-created_at"))


def get_approved_leave_years(user_id: int) -> list[dict]:
    """Return a list of approved leave applications with year/period info."""
    from django.db.models import F
    return list(LeaveApplication.objects.filter(
        user_id=user_id,
        status="sanctioned",
    ).annotate(
        year=F("requested_start__year"),
    ).values("year").distinct())


def get_substitute_nominations(application_id: int) -> list[SubstituteNomination]:
    """Return substitute nominations for a given application."""
    from modules.elm.models import SubstituteNomination
    return list(SubstituteNomination.objects.filter(
        application_id=application_id,
        accepted=False,
    ))


def get_sla_status() -> dict:
    """Return SLA threshold configuration (placeholder)."""
    return {"reminder_threshold_hours": 48, "escalation_threshold_hours": 72}