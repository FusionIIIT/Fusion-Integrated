"""Archival selectors for System Admin module.

Enforces read-only inspection of archived records, archived users, and purge requests
(CFR-SA-014, AFR-SA-056, AFR-SA-058, BR-SA-020).
"""
from datetime import date
from django.db.models import QuerySet

from modules.system_admin.models import ArchivedRecord, BasicUser, PurgeRequest


def list_archived_records(
    category: str | None = None,
    status: str = "archived",
    from_date: date | None = None,
    to_date: date | None = None,
) -> QuerySet[ArchivedRecord]:
    qs = ArchivedRecord.objects.filter(status=status).order_by("-archived_at")
    if category:
        qs = qs.filter(category=category)
    if from_date:
        qs = qs.filter(archived_at__date__gte=from_date)
    if to_date:
        qs = qs.filter(archived_at__date__lte=to_date)
    return qs


def get_archived_record(archive_id: int) -> ArchivedRecord | None:
    return ArchivedRecord.objects.filter(id=archive_id).first()


def list_archived_users(
    user_type: str | None = None,
    department: str | None = None,
    search: str | None = None,
) -> QuerySet[BasicUser]:
    """Lists archived users with read-only filter (AFR-SA-049B, AFR-SA-058)."""
    qs = BasicUser.objects.filter(status="archived").order_by("-archived_at")
    if user_type:
        qs = qs.filter(user_type=user_type)
    if department:
        qs = qs.filter(department__iexact=department)
    if search and search.strip():
        term = search.strip()
        qs = qs.filter(
            institute_id__icontains=term
            | BasicUser.objects.filter(first_name__icontains=term)
            | BasicUser.objects.filter(last_name__icontains=term)
        )
    return qs


def list_purge_requests(status: str = "pending_it_head") -> QuerySet[PurgeRequest]:
    return (
        PurgeRequest.objects.filter(status=status)
        .select_related("archived_record")
        .order_by("-requested_at")
    )


def get_purge_request(request_id: int) -> PurgeRequest | None:
    return (
        PurgeRequest.objects.filter(id=request_id)
        .select_related("archived_record")
        .first()
    )
