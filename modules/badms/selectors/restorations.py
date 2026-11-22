"""Read-only selectors for data restoration requests."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.badms.models import RestorationRequest


def list_restorations(
    *,
    user_id: int | None = None,
    status: str | None = None,
) -> QuerySet[RestorationRequest]:
    qs = RestorationRequest.objects.all().select_related("archival_request").order_by("-created_at")
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_restoration_by_id(restoration_id: int) -> RestorationRequest | None:
    return (
        RestorationRequest.objects.filter(id=restoration_id)
        .select_related("archival_request")
        .first()
    )


def list_sysadmin_restoration_queue() -> QuerySet[RestorationRequest]:
    """Sensitive restoration requests pending approval or ready for execution."""
    return (
        RestorationRequest.objects.filter(
            status__in=["pending_approval", "requested_standard", "approved"]
        )
        .select_related("archival_request")
        .order_by("-created_at")
    )
