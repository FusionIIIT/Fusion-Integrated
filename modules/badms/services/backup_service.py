"""Backup management service (CFR-BA-001, CFR-BA-002, CFR-BA-016)."""

from __future__ import annotations

import hashlib

from django.db import transaction
from django.utils import timezone

from modules.badms.domain.entities import ActorRole
from modules.badms.domain.errors import BadmsDomainError
from modules.badms.domain.rules import (
    check_manual_backup_auth,
    check_repository_reachability,
    evaluate_failure_alerts,
)
from modules.badms.models import BackupRecord, BackupSchedule, SystemState
from modules.badms.services.audit_service import record_audit_event
from modules.badms.services.notification_service import (
    alert_sysadmin_backup_failure,
    escalate_repeated_backup_failures,
)


@transaction.atomic
def trigger_manual_backup(
    *,
    actor_id: int,
    actor_username: str,
    actor_role: str,
    dataset: str = "all",
    repository_path: str = "/var/backups/fusion",
) -> BackupRecord:
    """BA-UC-001: SysAdmin or Super Admin triggers on-demand manual backup."""
    role_enum = (
        ActorRole(actor_role) if actor_role in [r.value for r in ActorRole] else ActorRole.USER
    )
    check_manual_backup_auth(role_enum)

    backup = BackupRecord.objects.create(
        backup_type="manual",
        status="in_progress",
        trigger_user_id=actor_id,
        dataset=dataset,
        repository_path=repository_path,
        started_at=timezone.now(),
    )

    try:
        # Simulate dump creation and checksum verification
        artifact_name = f"dump_{dataset}_{int(timezone.now().timestamp())}.sql.gz"
        artifact_path = f"{repository_path.rstrip('/')}/{artifact_name}"
        checksum = hashlib.sha256(artifact_path.encode()).hexdigest()

        backup.status = "success"
        backup.artifact_path = artifact_path
        backup.checksum = checksum
        backup.size_bytes = 10485760  # 10 MB simulated state dump
        backup.is_consistent = True
        backup.completed_at = timezone.now()
        backup.save()

        # Reset consecutive failures on success
        SystemState.objects.update_or_create(
            key="consecutive_backup_failures",
            defaults={"value_int": 0},
        )

        record_audit_event(
            actor_id=actor_id,
            actor_username=actor_username,
            actor_role=actor_role,
            event_source="admin",
            action="manual_backup_executed",
            resource_type="BackupRecord",
            resource_id=str(backup.id),
            outcome="success",
            details={"dataset": dataset, "artifact_path": artifact_path},
        )
    except (BadmsDomainError, OSError, RuntimeError, ValueError) as exc:
        return _handle_backup_failure_internal(
            backup, str(exc), actor_id, actor_username, actor_role
        )
    else:
        return backup


@transaction.atomic
def execute_scheduled_backup(
    *,
    schedule: BackupSchedule,
    is_reachable: bool = True,
) -> BackupRecord:
    """BA-UC-006: Execute scheduled automatic backup."""
    backup = BackupRecord.objects.create(
        schedule=schedule,
        backup_type="automatic",
        status="in_progress",
        dataset=schedule.dataset,
        repository_path=schedule.repository_path,
        started_at=timezone.now(),
    )

    try:
        check_repository_reachability(is_reachable, schedule.repository_path)

        artifact_name = f"auto_{schedule.dataset}_{int(timezone.now().timestamp())}.sql.gz"
        artifact_path = f"{schedule.repository_path.rstrip('/')}/{artifact_name}"
        checksum = hashlib.sha256(artifact_path.encode()).hexdigest()

        backup.status = "success"
        backup.artifact_path = artifact_path
        backup.checksum = checksum
        backup.size_bytes = 20971520  # 20 MB simulated
        backup.is_consistent = True
        backup.completed_at = timezone.now()
        backup.save()

        SystemState.objects.update_or_create(
            key="consecutive_backup_failures",
            defaults={"value_int": 0},
        )

        record_audit_event(
            actor_id=None,
            actor_username="system_scheduler",
            actor_role="system",
            event_source="system",
            action="scheduled_backup_executed",
            resource_type="BackupRecord",
            resource_id=str(backup.id),
            outcome="success",
            details={"schedule_id": schedule.id, "dataset": schedule.dataset},
        )
    except (BadmsDomainError, OSError, RuntimeError, ValueError) as exc:
        return _handle_backup_failure_internal(backup, str(exc), None, "system_scheduler", "system")
    else:
        return backup


def _handle_backup_failure_internal(
    backup: BackupRecord,
    error_message: str,
    actor_id: int | None,
    actor_username: str,
    actor_role: str,
) -> BackupRecord:
    backup.status = "failure"
    backup.error_message = error_message
    backup.completed_at = timezone.now()
    backup.save()

    # Track consecutive failures
    state, _ = SystemState.objects.get_or_create(
        key="consecutive_backup_failures", defaults={"value_int": 0}
    )
    consecutive = state.value_int + 1
    state.value_int = consecutive
    state.save()

    alerts = evaluate_failure_alerts(consecutive)
    if alerts["alert_sysadmin"]:
        alert_sysadmin_backup_failure(backup.id, error_message)
    if alerts["escalate_director_it"]:
        escalate_repeated_backup_failures(consecutive)

    record_audit_event(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        event_source="system" if actor_role == "system" else "admin",
        action="backup_failed",
        resource_type="BackupRecord",
        resource_id=str(backup.id),
        outcome="failure",
        details={"error": error_message, "consecutive_failures": consecutive},
    )
    return backup
