"""Read selectors for Leave Applications."""

from __future__ import annotations

from collections.abc import Sequence

from django.db.models import QuerySet

from modules.elm.domain.state_machine import ACTIVE_LEAVE_STATES
from modules.elm.models import LeaveApplication


def get_user_applications(user_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")


def get_application_by_id(application_id: int) -> LeaveApplication | None:
    try:
        return LeaveApplication.objects.get(id=application_id)
    except LeaveApplication.DoesNotExist:
        return None


def get_active_leaves_for_user(user_id: int) -> Sequence[dict]:
    """Return dictionary representations of active leaves for overlap checking."""
    leaves = LeaveApplication.objects.filter(
        user_id=user_id,
        status__in=ACTIVE_LEAVE_STATES,
    ).values("start_date", "end_date", "leave_category", "half_day", "half_day_type", "status")
    return list(leaves)


def get_pending_substitute_requests(substitute_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(
        substitute_id=substitute_id,
        substitute_status="pending",
        status__in=["awaiting_substitute", "awaiting_ext_substitute"],
    ).order_by("-created_at")


def get_pending_unit_head_reviews() -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(
        status__in=[
            "awaiting_unit_head",
            "cancellation_pending_unit_head",
            "awaiting_ext_unit_head",
        ]
    ).order_by("-created_at")


def get_pending_establishment_reviews() -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(
        status__in=[
            "awaiting_establishment",
            "cancellation_pending_establishment",
            "ext_pending_establishment",
        ]
    ).order_by("-created_at")


def get_pending_sanctions() -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(
        status__in=[
            "awaiting_final_sanction",
            "awaiting_director_self_sanction",
            "cancellation_pending_final",
            "ext_pending_final",
            "resumption_review_pending",
        ]
    ).order_by("-created_at")
