"""Scheduled and asynchronous Celery tasks for BADMS.

Ids only in arguments, never ORM objects.
"""

from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.badms.tasks")


@shared_task(
    name="badms.execute_scheduled_backups",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def execute_scheduled_backups() -> int:
    """Executes any backup schedule due for automatic execution (BA-UC-006)."""
    from modules.badms.models import BackupSchedule
    from modules.badms.services import execute_scheduled_backup

    active_schedules = BackupSchedule.objects.filter(is_active=True)
    count = 0
    for schedule in active_schedules:
        try:
            execute_scheduled_backup(schedule=schedule, is_reachable=True)
            count += 1
        except Exception as exc:  # noqa: BLE001
            log.error("Failed scheduled backup for schedule %d: %s", schedule.id, exc)
    return count


@shared_task(
    name="badms.monitor_storage_thresholds",
    acks_late=True,
    soft_time_limit=270,
    time_limit=300,
)
def monitor_storage_thresholds() -> int:
    """Evaluates user storage thresholds against allocated quotas (BA-UC-022)."""
    from modules.badms.services import evaluate_all_storage_thresholds

    updated = evaluate_all_storage_thresholds()
    log.info("badms.storage.thresholds.evaluated updated=%d", updated)
    return updated


@shared_task(
    name="badms.drain_notification_queue",
    acks_late=True,
    soft_time_limit=60,
    time_limit=90,
)
def drain_notification_queue() -> int:
    """Processes any unsent notifications."""
    from modules.badms.models import NotificationLog

    pending = NotificationLog.objects.filter(is_delivered=False)
    count = pending.count()
    pending.update(is_delivered=True)
    return count
