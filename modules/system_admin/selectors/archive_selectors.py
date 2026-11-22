"""Read selectors for archived users, historical datasets, and purge requests."""
from __future__ import annotations

from django.db.models import Q

from modules.system_admin.models.archive import (
    ArchivedUserRecord,
    HistoricalDatasetArchive,
    PermanentPurgeRequest,
)


def get_archived_user(user_id: int) -> ArchivedUserRecord | None:
    """Retrieve archived user record by user_id."""
    return ArchivedUserRecord.objects.filter(user_id=user_id).first()


def list_archived_users(
    *,
    query: str | None = None,
    user_type: str | None = None,
    retention_option: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ArchivedUserRecord], int]:
    """Search and filter archived user records (AFR-SA-058)."""
    qs = ArchivedUserRecord.objects.all()

    if user_type:
        qs = qs.filter(user_type=user_type.strip().lower())
    if retention_option:
        qs = qs.filter(retention_option=retention_option.strip())
    if query:
        q = query.strip()
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(institute_id__icontains=q)
            | Q(email__icontains=q)
            | Q(reason__icontains=q)
        )

    total = qs.count()
    records = list(qs[offset : offset + limit])
    return records, total


def list_historical_archives(
    *, category: str | None = None
) -> list[HistoricalDatasetArchive]:
    """List historical dataset archives (AFR-SA-056)."""
    qs = HistoricalDatasetArchive.objects.all()
    if category:
        qs = qs.filter(category__iexact=category.strip())
    return list(qs)


def list_purge_requests(
    *, status: str | None = None
) -> list[PermanentPurgeRequest]:
    """List permanent purge requests (AFR-SA-061A/B)."""
    qs = PermanentPurgeRequest.objects.all()
    if status:
        qs = qs.filter(status=status.strip().lower())
    return list(qs)
