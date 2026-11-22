"""Read-only selectors for backup records and backup schedules."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.badms.models import BackupRecord, BackupSchedule


def list_backups(
    *,
    status: str | None = None,
    backup_type: str | None = None,
    dataset: str | None = None,
) -> QuerySet[BackupRecord]:
    qs = BackupRecord.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if backup_type:
        qs = qs.filter(backup_type=backup_type)
    if dataset:
        qs = qs.filter(dataset=dataset)
    return qs


def get_backup_by_id(backup_id: int) -> BackupRecord | None:
    return BackupRecord.objects.filter(id=backup_id).first()


def list_schedules(
    *, scope: str | None = None, is_active: bool | None = None
) -> QuerySet[BackupSchedule]:
    qs = BackupSchedule.objects.all().order_by("name")
    if scope:
        qs = qs.filter(scope=scope)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_schedule_by_id(schedule_id: int) -> BackupSchedule | None:
    return BackupSchedule.objects.filter(id=schedule_id).first()


def get_effective_schedule(dataset: str) -> BackupSchedule | None:
    """BR-BA-011: Local schedule for dataset overrides global schedule."""
    local = BackupSchedule.objects.filter(scope="local", dataset=dataset, is_active=True).first()
    if local:
        return local
    return BackupSchedule.objects.filter(scope="global", is_active=True).first()
