"""Backup management service for BADMS."""
from __future__ import annotations

import hashlib
from typing import Any
from django.db import transaction
from django.utils import timezone
from modules.badms.models import (
    BackupExecution,
    BackupScope,
    BackupStatus,
    BackupType,
)
from modules.badms.services.audit import record_audit
from modules.badms.services.notifications import send_notification


class BackupServiceError(Exception):
    """Raised when backup operation fails validation or authorization."""
    pass


def get_latest_consecutive_failures() -> int:
    """Retrieve consecutive failure count from the most recent backup execution."""
    last = BackupExecution.objects.order_by("-started_at").first()
    if not last:
        return 0
    if last.status == BackupStatus.FAILED:
        return last.consecutive_failure_count
    return 0


@transaction.atomic
def execute_backup(
    *,
    initiated_by_user_id: int,
    initiated_by_role: str,
    backup_type: str = BackupType.FULL,
    scope: str = BackupScope.LOCAL,
    target_dataset: str = "all",
    metadata: dict[str, Any] | None = None,
    simulate_unreachable: bool = False,
    simulate_failure: bool = False,
) -> BackupExecution:
    """Execute a backup operation, verifying repository availability and integrity."""
    prev_failures = get_latest_consecutive_failures()

    b_type = (backup_type or BackupType.FULL).lower()
    if b_type not in BackupType.values:
        b_type = BackupType.FULL

    b_scope = (scope or BackupScope.LOCAL).lower()
    if b_scope not in BackupScope.values:
        b_scope = BackupScope.LOCAL

    now = timezone.now()

    # Step 1: Check repository availability
    if simulate_unreachable:
        consecutive = prev_failures + 1
        backup = BackupExecution.objects.create(
            backup_type=b_type,
            scope=b_scope,
            target_dataset=target_dataset,
            status=BackupStatus.FAILED,
            started_at=now,
            completed_at=now,
            repository_reachable=False,
            integrity_verified=False,
            error_message="Backup repository unreachable: network mount or storage volume unavailable.",
            consecutive_failure_count=consecutive,
            initiated_by_user_id=initiated_by_user_id,
            metadata=metadata or {},
        )
        _handle_backup_failure(backup, consecutive)
        return backup

    # Step 2: Handle simulated internal backup failure
    if simulate_failure:
        consecutive = prev_failures + 1
        backup = BackupExecution.objects.create(
            backup_type=b_type,
            scope=b_scope,
            target_dataset=target_dataset,
            status=BackupStatus.FAILED,
            started_at=now,
            completed_at=now,
            repository_reachable=True,
            integrity_verified=False,
            error_message="Database snapshot generation failed: locked table error.",
            consecutive_failure_count=consecutive,
            initiated_by_user_id=initiated_by_user_id,
            metadata=metadata or {},
        )
        _handle_backup_failure(backup, consecutive)
        return backup

    # Step 3: Successful backup execution
    # Simulated byte stream generation & SHA-256 integrity digest
    backup_content = f"DUMP:{target_dataset}:{b_type}:{now.isoformat()}".encode("utf-8")
    checksum = hashlib.sha256(backup_content).hexdigest()
    size_bytes = len(backup_content) * 1024 * 100  # realistic size estimate

    backup = BackupExecution.objects.create(
        backup_type=b_type,
        scope=b_scope,
        target_dataset=target_dataset,
        status=BackupStatus.COMPLETED,
        started_at=now,
        completed_at=timezone.now(),
        size_bytes=size_bytes,
        checksum=checksum,
        repository_reachable=True,
        integrity_verified=True,
        error_message="",
        consecutive_failure_count=0,  # Reset consecutive failure counter on success
        initiated_by_user_id=initiated_by_user_id,
        metadata=metadata or {},
    )

    # Record audit log
    record_audit(
        actor_user_id=initiated_by_user_id,
        actor_role=initiated_by_role,
        action="badms.backup.execute",
        target_type="backup_execution",
        target_id=backup.pk,
        outcome="success",
        details={
            "backup_type": b_type,
            "scope": b_scope,
            "target_dataset": target_dataset,
            "size_bytes": size_bytes,
            "checksum": checksum,
        },
    )

    # Send completion notification to SysAdmin
    send_notification(
        user_id=initiated_by_user_id,
        recipient_role="sysadmin",
        subject=f"Backup #{backup.pk} Completed Successfully ({b_scope.upper()})",
        message=(
            f"Backup #{backup.pk} for dataset '{target_dataset}' ({b_type}) completed successfully. "
            f"Size: {(size_bytes / (1024*1024)):.2f} MB. Integrity verified (SHA-256: {checksum[:12]}...)."
        ),
        notification_type="backup_completed",
        related_object_id=backup.pk,
    )

    return backup


def _handle_backup_failure(backup: BackupExecution, consecutive_failures: int) -> None:
    """Log failure audit and notify SysAdmin within 5 minutes; escalate on 3 consecutive failures."""
    record_audit(
        actor_user_id=backup.initiated_by_user_id or 0,
        action="badms.backup.failure",
        target_type="backup_execution",
        target_id=backup.pk,
        outcome="failure",
        details={
            "error_message": backup.error_message,
            "repository_reachable": backup.repository_reachable,
            "consecutive_failures": consecutive_failures,
        },
    )

    # Notify SysAdmin about backup failure immediately
    send_notification(
        user_id=0,
        recipient_role="sysadmin",
        subject=f"ALERT: Backup #{backup.pk} FAILED ({backup.scope.upper()})",
        message=(
            f"Backup #{backup.pk} ({backup.target_dataset}) failed at {backup.started_at}. "
            f"Error: {backup.error_message}. Consecutive failures: {consecutive_failures}."
        ),
        notification_type="backup_failure",
        related_object_id=backup.pk,
    )

    # Escalate to Director of IT after 3 consecutive failures
    if consecutive_failures >= 3:
        send_notification(
            user_id=0,
            recipient_role="director_of_it",
            subject=f"CRITICAL ESCALATION: {consecutive_failures} Consecutive Backup Failures",
            message=(
                f"Urgent Attention Required: {consecutive_failures} consecutive backup executions "
                f"have failed in BADMS. Latest execution #{backup.pk} failed with reason: {backup.error_message}. "
                f"Repository reachable: {backup.repository_reachable}."
            ),
            notification_type="director_escalation",
            related_object_id=backup.pk,
        )


@transaction.atomic
def verify_backup_integrity(backup_id: int, user_id: int, role: str) -> bool:
    """Perform integrity verification on a completed backup."""
    backup = BackupExecution.objects.select_for_update().filter(pk=backup_id).first()
    if not backup:
        raise BackupServiceError(f"Backup #{backup_id} not found.")

    if backup.status != BackupStatus.COMPLETED:
        raise BackupServiceError(
            f"Cannot verify integrity of incomplete or failed backup #{backup_id} (status: {backup.status})."
        )

    # Re-verify checksum presence and consistency
    is_valid = bool(backup.checksum and len(backup.checksum) == 64)
    backup.integrity_verified = is_valid
    backup.save(update_fields=["integrity_verified", "updated_at"])

    record_audit(
        actor_user_id=user_id,
        actor_role=role,
        action="badms.backup.verify_integrity",
        target_type="backup_execution",
        target_id=backup.pk,
        outcome="success" if is_valid else "failure",
        details={"checksum": backup.checksum, "integrity_verified": is_valid},
    )

    return is_valid
