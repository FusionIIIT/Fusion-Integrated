from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from fusion_auth.principal import Principal
from modules.superadmin.domain.constants import (
    AUDIT_ACTION_DATASET_ARCHIVED,
    AUDIT_ACTION_DATASET_RESTORED,
)
from modules.superadmin.models.archival import HistoricalDataArchive
from modules.superadmin.services.audit import record_audit_event


@transaction.atomic
def create_historical_archive(
    principal: Principal,
    *,
    dataset_category: str,
    title: str,
    date_range_start: date,
    date_range_end: date,
    record_count: int,
    backup_file_path: str,
    backup_checksum: str,
    retention_expires_at: date,
    summary_metadata: dict[str, Any] | None = None,
) -> HistoricalDataArchive:
    # Verifies pre-archive backup checksum presence and valid date bounds
    if date_range_end < date_range_start:
        raise DomainError("date_range_end must be greater than or equal to date_range_start.")
    if retention_expires_at < date_range_end:
        raise DomainError("retention_expires_at must be greater than or equal to date_range_end.")
    if not backup_checksum:
        raise DomainError("A verified cryptographic backup checksum is mandatory (BR-SA-018).")

    archive = HistoricalDataArchive.objects.create(
        dataset_category=dataset_category,
        title=title,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        record_count=record_count,
        backup_file_path=backup_file_path,
        backup_checksum=backup_checksum,
        retention_expires_at=retention_expires_at,
        archived_by=principal.user_id,
        summary_metadata=summary_metadata or {},
    )

    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "super_admin",
        action=AUDIT_ACTION_DATASET_ARCHIVED,
        target_id=str(archive.id),
        target_type="historical_archive",
        reason="Historical dataset archival executed.",
        context_metadata={"checksum": backup_checksum, "category": dataset_category},
    )
    return archive


@transaction.atomic
def restore_historical_archive(
    principal: Principal,
    *,
    archive_id: int,
) -> HistoricalDataArchive:
    archive = HistoricalDataArchive.objects.select_for_update().filter(id=archive_id).first()
    if archive is None:
        raise NotFoundError(f"Historical archive {archive_id} not found.")
    if archive.is_purged:
        raise ConflictError("This dataset was permanently purged and cannot be restored.")
    if archive.is_restored:
        raise ConflictError("This dataset has already been restored.")

    archive.is_restored = True
    archive.restored_at = timezone.now()
    archive.save(update_fields=["is_restored", "restored_at", "updated_at"])

    record_audit_event(
        actor_id=principal.user_id,
        actor_username=principal.username,
        actor_role=principal.active_role or "super_admin",
        action=AUDIT_ACTION_DATASET_RESTORED,
        target_id=str(archive.id),
        target_type="historical_archive",
        reason="Historical dataset restored to operational tier.",
    )
    return archive
