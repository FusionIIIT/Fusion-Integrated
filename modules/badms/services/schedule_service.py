"""Backup schedule configuration service (CFR-BA-003, CFR-BA-014)."""

from __future__ import annotations

from django.db import transaction

from modules.badms.domain.entities import ActorRole
from modules.badms.domain.errors import RuleViolation
from modules.badms.domain.rules import (
    check_global_backup_auth,
    validate_schedule_parameters,
)
from modules.badms.models import BackupSchedule
from modules.badms.services.audit_service import record_audit_event


@transaction.atomic
def create_schedule(
    *,
    actor_id: int,
    actor_username: str,
    actor_role: str,
    name: str,
    scope: str,
    dataset: str,
    frequency: str,
    execution_time: str,
    classification_filter: str = "ALL",
    repository_path: str = "/var/backups/fusion",
) -> BackupSchedule:
    role_enum = (
        ActorRole(actor_role) if actor_role in [r.value for r in ActorRole] else ActorRole.USER
    )

    if scope == "global":
        check_global_backup_auth(role_enum)

    valid, err_msg = validate_schedule_parameters(frequency, execution_time, dataset)
    if not valid:
        raise RuleViolation("BR-BA-012", err_msg)

    schedule, created = BackupSchedule.objects.update_or_create(
        scope=scope,
        dataset=dataset,
        defaults={
            "name": name,
            "frequency": frequency,
            "execution_time": execution_time,
            "classification_filter": classification_filter,
            "repository_path": repository_path,
            "is_active": True,
            "created_by_id": actor_id,
        },
    )

    record_audit_event(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        event_source="admin",
        action="schedule_created" if created else "schedule_updated",
        resource_type="BackupSchedule",
        resource_id=str(schedule.id),
        outcome="success",
        details={"name": name, "scope": scope, "dataset": dataset, "frequency": frequency},
    )
    return schedule
