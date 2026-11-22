"""Archive and purge selectors for Super Admin."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.superadmin.models import HistoricalArchiveRecord, PurgeRequestRecord
from modules.superadmin.selectors.scoping import visible_archives


def list_archives(
    principal,
    *,
    entity_type: str = "",
    status: str = "",
) -> QuerySet[HistoricalArchiveRecord]:
    qs = visible_archives(principal)
    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    if status:
        qs = qs.filter(status=status.upper())
    return qs.order_by("-created_at")


def get_archive_by_id(principal, archive_id: int) -> HistoricalArchiveRecord | None:
    return visible_archives(principal).filter(pk=archive_id).first()


def list_purge_requests(principal, *, status: str = "") -> QuerySet[PurgeRequestRecord]:
    qs = PurgeRequestRecord.objects.select_related("archive_record")
    if status:
        qs = qs.filter(status=status.upper())
    return qs.order_by("-created_at")


def get_purge_request_by_id(principal, request_id: int) -> PurgeRequestRecord | None:
    return PurgeRequestRecord.objects.select_related("archive_record").filter(pk=request_id).first()
