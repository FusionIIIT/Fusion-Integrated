"""Archival and purge selectors for system_admin."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Optional, Tuple

from django.db.models import Q

from modules.system_admin.constants import PurgeRequestStatus, UserArchivalStatus
from modules.system_admin.models import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)


def list_archived_users(
    *,
    status: Optional[str] = None,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> Tuple[Sequence[ArchivedUserRecord], int]:
    """List archived user records with optional status filter and search query."""
    qs = ArchivedUserRecord.objects.all().order_by("-archived_at")
    if status:
        qs = qs.filter(status=status)
    if q:
        query = q.strip()
        qs = qs.filter(
            Q(username__icontains=query)
            | Q(institute_id__icontains=query)
            | Q(email__icontains=query)
        )
    total = qs.count()
    return list(qs[offset : offset + limit]), total


def get_archived_user(basic_user_id: int) -> Optional[ArchivedUserRecord]:
    """Retrieve archived user record by original basic_user_id."""
    return ArchivedUserRecord.objects.filter(basic_user_id=basic_user_id).first()


def get_expired_reversible_user_records(now: datetime) -> Sequence[ArchivedUserRecord]:
    """Find accounts in REVERSIBLE state whose reversibility window has expired (BW-SA-08, ISS-SA-004)."""
    return list(
        ArchivedUserRecord.objects.filter(
            status=UserArchivalStatus.REVERSIBLE,
            reversible_until__lt=now,
        )
    )


def list_historical_archives(
    *, category: Optional[str] = None
) -> Sequence[HistoricalDataArchive]:
    """List archived datasets."""
    qs = HistoricalDataArchive.objects.all().order_by("-archived_at")
    if category:
        qs = qs.filter(dataset_category=category)
    return list(qs)


def get_historical_archive(archive_id: int) -> Optional[HistoricalDataArchive]:
    """Retrieve dataset archive record."""
    return HistoricalDataArchive.objects.filter(id=archive_id).first()


def list_purge_requests(
    *, status: Optional[str] = None
) -> Sequence[PurgeRequest]:
    """List purge requests."""
    qs = PurgeRequest.objects.select_related("archive").order_by("-requested_at")
    if status:
        qs = qs.filter(status=status)
    return list(qs)


def get_purge_request(request_id: int) -> Optional[PurgeRequest]:
    """Retrieve purge request by ID."""
    return PurgeRequest.objects.filter(id=request_id).select_related("archive").first()
