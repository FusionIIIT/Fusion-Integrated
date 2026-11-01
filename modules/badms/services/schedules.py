"""Backup scheduling, precedence resolution, and policy service for BADMS."""
from __future__ import annotations

from datetime import time
from typing import Any
from django.db import transaction
from modules.badms.models import (
    BackupExecution,
    BackupFrequency,
    BackupSchedule,
    BackupScope,
)
from modules.badms.services.audit import record_audit
from modules.badms.services.backup import execute_backup


class ScheduleValidationError(Exception):
    """Raised when a proposed schedule configuration is invalid."""
    pass


def validate_schedule_configuration(data: dict[str, Any]) -> dict[str, Any]:
    """Validate schedule parameters, rejecting invalid configurations without mutating state."""
    name = (data.get("name") or "").strip()
    if not name:
        raise ScheduleValidationError("Schedule name is required.")

    schedule_type = (data.get("schedule_type") or BackupScope.LOCAL).lower()
    if schedule_type not in BackupScope.values:
        raise ScheduleValidationError(
            f"Invalid schedule type '{schedule_type}'. Allowed: {list(BackupScope.values)}."
        )

    frequency = (data.get("frequency") or BackupFrequency.DAILY).lower()
    if frequency not in BackupFrequency.values:
        raise ScheduleValidationError(
            f"Invalid frequency '{frequency}'. Allowed: {list(BackupFrequency.values)}."
        )

    exec_time = data.get("execution_time")
    if not exec_time:
        raise ScheduleValidationError("Execution time is required.")
    if isinstance(exec_time, str):
        try:
            parts = [int(p) for p in exec_time.split(":")]
            if len(parts) == 2:
                exec_time = time(hour=parts[0], minute=parts[1])
            elif len(parts) == 3:
                exec_time = time(hour=parts[0], minute=parts[1], second=parts[2])
            else:
                raise ValueError()
        except (ValueError, TypeError):
            raise ScheduleValidationError("Invalid execution time format. Expected HH:MM or HH:MM:SS.")

    repo_path = (data.get("repository_path") or "").strip()
    if not repo_path or not repo_path.startswith("/"):
        raise ScheduleValidationError("Repository path must be an absolute path.")

    return {
        "name": name,
        "schedule_type": schedule_type,
        "target_dataset": (data.get("target_dataset") or "all").strip(),
        "frequency": frequency,
        "execution_time": exec_time,
        "classification_filter": (data.get("classification_filter") or "all").strip(),
        "repository_path": repo_path,
        "is_active": bool(data.get("is_active", True)),
    }


def get_effective_schedule(target_dataset: str = "all") -> BackupSchedule | None:
    """Resolve the effective schedule according to precedence rules:

    1. A valid, active local schedule matching the dataset (or 'all') overrides the global schedule.
    2. The global schedule applies when no valid local schedule exists.
    """
    # Check for active local schedule first (local override)
    local_schedule = BackupSchedule.objects.filter(
        schedule_type=BackupScope.LOCAL,
        is_active=True,
    ).filter(
        target_dataset__in=[target_dataset, "all"]
    ).order_by("-created_at").first()

    if local_schedule:
        return local_schedule

    # Fall back to global schedule
    global_schedule = BackupSchedule.objects.filter(
        schedule_type=BackupScope.GLOBAL,
        is_active=True,
    ).order_by("-created_at").first()

    return global_schedule


@transaction.atomic
def create_schedule(
    *,
    user_id: int,
    user_role: str,
    payload: dict[str, Any],
) -> BackupSchedule:
    """Validate and persist a new backup schedule."""
    validated = validate_schedule_configuration(payload)

    schedule = BackupSchedule.objects.create(
        name=validated["name"],
        schedule_type=validated["schedule_type"],
        target_dataset=validated["target_dataset"],
        frequency=validated["frequency"],
        execution_time=validated["execution_time"],
        classification_filter=validated["classification_filter"],
        repository_path=validated["repository_path"],
        is_active=validated["is_active"],
        created_by_user_id=user_id,
    )

    record_audit(
        actor_user_id=user_id,
        actor_role=user_role,
        action="badms.schedule.create",
        target_type="backup_schedule",
        target_id=schedule.pk,
        outcome="success",
        details={
            "name": schedule.name,
            "schedule_type": schedule.schedule_type,
            "frequency": schedule.frequency,
        },
    )

    return schedule


@transaction.atomic
def execute_scheduled_backup(
    schedule_id: int,
    *,
    user_id: int = 0,
    simulate_unreachable: bool = False,
) -> BackupExecution:
    """Execute a scheduled backup according to its configured schedule and reachability."""
    schedule = BackupSchedule.objects.select_for_update().filter(pk=schedule_id).first()
    if not schedule:
        raise ScheduleValidationError(f"Schedule #{schedule_id} does not exist.")

    if not schedule.is_active:
        raise ScheduleValidationError(f"Schedule #{schedule_id} is inactive.")

    return execute_backup(
        initiated_by_user_id=user_id,
        initiated_by_role="scheduler",
        backup_type="full",
        scope=schedule.schedule_type,
        target_dataset=schedule.target_dataset,
        metadata={"schedule_id": schedule.pk, "schedule_name": schedule.name},
        simulate_unreachable=simulate_unreachable,
    )
