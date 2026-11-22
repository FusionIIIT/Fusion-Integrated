"""Read selectors for FTS governance and audit logs."""
from __future__ import annotations

from typing import Any

from django.db.models import Count, QuerySet

from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
)
from modules.fts.models.audit import FileAuditLog
from modules.fts.models.files import File
from modules.fts.models.movements import FileMovement


def get_audit_logs(file_id: int | None = None) -> QuerySet[FileAuditLog]:
    """Returns audit log records, optionally filtered by file_id."""
    qs = FileAuditLog.objects.all().order_by("-timestamp")
    if file_id is not None:
        qs = qs.filter(file_id=file_id)
    return qs


def get_usage_metrics() -> dict[str, Any]:
    """Computes aggregate usage metrics for System Admin monitoring."""
    total_files = File.objects.count()
    status_counts = dict(
        File.objects.values("status").annotate(count=Count("id")).values_list("status", "count")
    )
    total_movements = FileMovement.objects.count()

    return {
        "total_files": total_files,
        "draft_files": status_counts.get(STATE_DRAFT, 0),
        "circulated_files": status_counts.get(STATE_CIRCULATED, 0),
        "archived_files": status_counts.get(STATE_ARCHIVED, 0),
        "discarded_drafts": status_counts.get(STATE_DISCARDED, 0),
        "total_movements": total_movements,
    }
