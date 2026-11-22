import hashlib
from datetime import UTC, datetime

from django.db import transaction

from modules.badms.models import BackupRecord
from modules.badms.services.audit import log_audit_event
from modules.badms.services.notifications import (
    send_backup_failure_alert,
    send_backup_failure_escalation,
)


def _compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@transaction.atomic
def trigger_manual_backup(actor, dataset_name: str) -> BackupRecord:
    user_id = getattr(actor, "user_id", None) or 0
    now = datetime.now(UTC)
    mock_payload = f"DUMP-{dataset_name}-{now.isoformat()}".encode()
    checksum = _compute_checksum(mock_payload)
    record = BackupRecord.objects.create(
        backup_type=BackupRecord.TYPE_MANUAL,
        dataset_name=dataset_name,
        status=BackupRecord.STATUS_SUCCESS,
        started_at=now,
        completed_at=now,
        file_path=f"/var/backups/badms/{dataset_name}_{int(now.timestamp())}.dump",
        file_size_bytes=len(mock_payload),
        checksum_sha256=checksum,
        triggered_by_user_id=user_id,
        consecutive_failure_count=0,
    )
    log_audit_event("manual_backup_created", actor, "BackupRecord", record.id)
    return record


@transaction.atomic
def execute_scheduled_backup(
    dataset_name: str,
    repository_reachable: bool = True,
    simulate_failure: bool = False,
) -> BackupRecord:
    now = datetime.now(UTC)
    last_record = (
        BackupRecord.objects.filter(dataset_name=dataset_name).order_by("-created_at").first()
    )
    prev_failures = last_record.consecutive_failure_count if last_record else 0

    if not repository_reachable or simulate_failure:
        failure_count = prev_failures + 1
        record = BackupRecord.objects.create(
            backup_type=BackupRecord.TYPE_SCHEDULED,
            dataset_name=dataset_name,
            status=BackupRecord.STATUS_FAILURE,
            started_at=now,
            completed_at=now,
            error_message="Target backup repository is unreachable or dump failed.",
            consecutive_failure_count=failure_count,
            alert_sent=True,
        )
        send_backup_failure_alert(record)
        if failure_count >= 3:
            send_backup_failure_escalation(record)
        return record

    mock_payload = f"SCHEDULED-DUMP-{dataset_name}-{now.isoformat()}".encode()
    checksum = _compute_checksum(mock_payload)
    return BackupRecord.objects.create(
        backup_type=BackupRecord.TYPE_SCHEDULED,
        dataset_name=dataset_name,
        status=BackupRecord.STATUS_SUCCESS,
        started_at=now,
        completed_at=now,
        file_path=f"/var/backups/badms/{dataset_name}_{int(now.timestamp())}.dump",
        file_size_bytes=len(mock_payload),
        checksum_sha256=checksum,
        consecutive_failure_count=0,
    )
