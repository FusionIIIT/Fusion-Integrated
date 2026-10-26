"""Ownership and role-based queryset scoping for leave applications and balances."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.leave.models import LeaveApplication, LeaveBalance


def is_approver(actor) -> bool:
    """True if actor holds authority to review or approve leave applications."""
    if actor is None:
        return False
    return (
        actor.has_permission("leave.application.approve")
        or actor.has_permission("leave.application.review")
    )


def applications_for(actor) -> QuerySet[LeaveApplication]:
    """Scope leave applications visible to the given actor.

    Approvers can access all applications.
    Regular employees can only view applications where they are the applicant
    or the nominated substitute.
    """
    if actor is None:
        return LeaveApplication.objects.none()

    if is_approver(actor):
        return LeaveApplication.objects.all()

    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        return LeaveApplication.objects.none()

    return LeaveApplication.objects.filter(
        Q(user_id=user_id) | Q(substitute_id=user_id)
    )


def balances_for(actor) -> QuerySet[LeaveBalance]:
    """Scope leave balances visible to the given actor.

    Holders of leave.balance.view can see all balances.
    Regular employees can only see their own leave balance.
    """
    if actor is None:
        return LeaveBalance.objects.none()

    if actor.has_permission("leave.balance.view"):
        return LeaveBalance.objects.all()

    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        return LeaveBalance.objects.none()

    return LeaveBalance.objects.filter(user_id=user_id)
