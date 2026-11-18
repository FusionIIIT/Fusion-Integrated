"""Every list view starts from a queryset built here.

Ownership is enforced by narrowing the queryset, never by fetching a row and
then checking it — so somebody else's leave is a 404, not a 403.
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.leave.models import LeaveApplication, LeaveBalance

P_REVIEW = "leave.request.review"
P_SANCTION = "leave.request.sanction"
P_MANAGE = "leave.policy.manage"


def is_approver(actor) -> bool:
    return actor is not None and actor.has_any_permission(P_REVIEW, P_SANCTION,
                                                          P_MANAGE)


def my_applications(actor) -> QuerySet[LeaveApplication]:
    return (LeaveApplication.objects
            .filter(user_id=actor.user_id)
            .order_by("-created_at"))


def my_balances(actor, year: str) -> QuerySet[LeaveBalance]:
    return (LeaveBalance.objects
            .filter(user_id=actor.user_id, year=year)
            .order_by("leave_type"))


def nominations_for(actor) -> QuerySet[LeaveApplication]:
    """Where this employee is the nominated substitute and consent is pending."""
    return (LeaveApplication.objects
            .filter(substitute_user_id=actor.user_id,
                    substitute_status="pending",
                    status="pending_substitute")
            .order_by("start_date"))


def review_queue(actor) -> QuerySet[LeaveApplication]:
    """Unit Head queue. An approver never reviews their own request."""
    return (LeaveApplication.objects
            .filter(status="pending_unit_head")
            .exclude(user_id=actor.user_id)
            .order_by("start_date"))


def sanction_queue(actor) -> QuerySet[LeaveApplication]:
    return (LeaveApplication.objects
            .filter(status="pending_authority")
            .exclude(user_id=actor.user_id)
            .order_by("start_date"))


def actionable(actor) -> QuerySet[LeaveApplication]:
    """Anything this actor may decide on, for the detail/decision endpoints."""
    codes = []
    if actor.has_permission(P_REVIEW):
        codes.append("pending_unit_head")
    if actor.has_permission(P_SANCTION):
        codes.append("pending_authority")
    return (LeaveApplication.objects
            .filter(status__in=codes)
            .exclude(user_id=actor.user_id))
