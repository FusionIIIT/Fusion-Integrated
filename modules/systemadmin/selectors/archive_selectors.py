"""Selectors for archival queries and purge requests."""

from django.db.models import QuerySet

from modules.systemadmin.models.archival import (
    ArchivedHistoricalData,
    ArchivedUser,
    PermanentPurgeRequest,
)


def list_archived_users(
    status: str | None = None,
    search: str | None = None,
) -> QuerySet[ArchivedUser]:
    """Retrieve archived users with optional status and search filtering."""
    qs = ArchivedUser.objects.select_related("user").all()
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = (
            qs.filter(user__institute_id__icontains=search)
            | qs.filter(user__institute_email__icontains=search)
            | qs.filter(reason__icontains=search)
        )
    return qs.order_by("-archived_at")


def get_archived_user(user_id: int) -> ArchivedUser | None:
    """Get single archived user by BasicUserProfile pk or ArchivedUser pk."""
    return ArchivedUser.objects.select_related("user").filter(user_id=user_id).first()


def list_archived_historical_data(
    category: str | None = None,
    status: str | None = None,
) -> QuerySet[ArchivedHistoricalData]:
    """Retrieve historical data archive batches."""
    qs = ArchivedHistoricalData.objects.all()
    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-archived_at")


def list_purge_requests(
    status: str | None = None,
    target_type: str | None = None,
) -> QuerySet[PermanentPurgeRequest]:
    """Retrieve permanent purge requests for IT Head authorization."""
    qs = PermanentPurgeRequest.objects.select_related(
        "historical_data", "archived_user__user"
    ).all()
    if status:
        qs = qs.filter(status=status)
    if target_type:
        qs = qs.filter(target_type=target_type)
    return qs.order_by("-requested_at")
