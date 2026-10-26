"""Selectors for substitute requests."""

from django.db.models import QuerySet

from modules.leave.models import LeaveApplication


def pending_substitute_tasks(user_id: int) -> QuerySet[LeaveApplication]:
    """Return applications where this user is nominated as substitute and decision is pending."""
    return LeaveApplication.objects.filter(
        substitute_user_id=user_id,
        status="AWAITING_SUBSTITUTE",
        substitute_status="PENDING",
    ).order_by("created_at")
