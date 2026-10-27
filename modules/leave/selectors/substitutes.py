"""Read queries for substitute requests."""
from __future__ import annotations

from django.db.models import QuerySet
from modules.leave.models import SubstituteRequest


def get_pending_substitute_requests(user_id: int) -> QuerySet[SubstituteRequest]:
    """Retrieve pending responsibility requests where user is the nominated substitute."""
    return SubstituteRequest.objects.filter(
        substitute_user_id=user_id,
        status="pending",
        is_current=True,
    ).select_related("application").order_by("-created_at")


def get_substitute_requests_for_application(application_id: int) -> QuerySet[SubstituteRequest]:
    return SubstituteRequest.objects.filter(application_id=application_id).order_by("-created_at")
