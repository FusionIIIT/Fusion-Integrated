"""Historical dataset archival and restoration service (BW-SA-09)."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.superadmin.models import ArchiveStatus, HistoricalArchiveRecord
from modules.superadmin.services.audit import log_audit_event


@transaction.atomic
def archive_historical_data(
    *,
    actor_user_id: int,
    entity_type: str,
    record_identifier: str,
    payload: dict,
    backup_reference: str,
    retention_period_days: int = 1825,
    ip_address: str | None = None,
) -> HistoricalArchiveRecord:
    # UC-SA-016 & BR-SA-018: Archive dataset with verified backup reference.
    if not backup_reference or not backup_reference.strip():
        raise ConflictError(
            "Backup reference is mandatory prior to archival.", code="missing_backup_reference"
        )

    now = timezone.now()
    purge_date = now + timedelta(days=retention_period_days)

    record = HistoricalArchiveRecord.objects.create(
        entity_type=entity_type,
        record_identifier=record_identifier,
        payload=payload,
        backup_reference=backup_reference,
        retention_period_days=retention_period_days,
        purge_eligible_at=purge_date,
        status=ArchiveStatus.ARCHIVED,
        archived_by_user_id=actor_user_id,
    )

    log_audit_event(
        event_type="HISTORICAL_DATA_ARCHIVED",
        actor_user_id=actor_user_id,
        target_entity="HistoricalArchiveRecord",
        target_id=str(record.pk),
        ip_address=ip_address,
        action_details={"entity_type": entity_type, "record_identifier": record_identifier},
    )
    return record


@transaction.atomic
def restore_historical_data(
    *,
    actor_user_id: int,
    archive_id: int,
    reason: str,
    ip_address: str | None = None,
) -> HistoricalArchiveRecord:
    # UC-SA-019 & BW-SA-09: Restore archived historical data.
    record = HistoricalArchiveRecord.objects.select_for_update().filter(pk=archive_id).first()
    if not record:
        raise NotFoundError("Archive record not found.", code="archive_not_found")

    if record.status == ArchiveStatus.PURGED:
        raise ConflictError("Purged data cannot be restored.", code="data_already_purged")

    if record.status != ArchiveStatus.ARCHIVED:
        raise ConflictError(
            f"Cannot restore record in status {record.status!r}.", code="invalid_archive_status"
        )

    record.status = ArchiveStatus.RESTORED
    record.save(update_fields=["status", "updated_at"])

    log_audit_event(
        event_type="HISTORICAL_DATA_RESTORED",
        actor_user_id=actor_user_id,
        target_entity="HistoricalArchiveRecord",
        target_id=str(archive_id),
        ip_address=ip_address,
        action_details={"reason": reason},
    )
    return record
