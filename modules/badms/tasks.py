from datetime import UTC, datetime

from celery import shared_task
from django.db import transaction

from modules.badms.models import ArchivalRequest, BackupRecord, BackupSchedule, UserStorageQuota
from modules.badms.services.backups import execute_scheduled_backup
from modules.badms.services.notifications import (
    send_backup_failure_alert,
    send_backup_failure_escalation,
)


@shared_task(name="badms.evaluate_and_dispatch_due_backups")
def evaluate_and_dispatch_due_backups():
    now = datetime.now(UTC)
    schedules = BackupSchedule.objects.filter(is_active=True)
    dispatched = 0
    for sched in schedules:
        with transaction.atomic():
            locked = (
                BackupSchedule.objects.select_for_update()
                .filter(id=sched.id, is_active=True)
                .first()
            )
            if not locked:
                continue
            execute_scheduled_backup(locked.dataset_name)
            locked.last_run_at = now
            locked.save(update_fields=["last_run_at"])
            dispatched += 1
    return {"dispatched": dispatched}


@shared_task(name="badms.check_backup_failure_sla")
def check_backup_failure_sla():
    recent_failures = BackupRecord.objects.filter(
        status=BackupRecord.STATUS_FAILURE, alert_sent=False
    )
    alerted = 0
    for rec in recent_failures:
        send_backup_failure_alert(rec)
        rec.alert_sent = True
        rec.save(update_fields=["alert_sent"])
        if rec.consecutive_failure_count >= 3:
            send_backup_failure_escalation(rec)
        alerted += 1
    return {"alerted": alerted}


@shared_task(name="badms.monitor_storage_thresholds")
def monitor_storage_thresholds():
    quotas = UserStorageQuota.objects.all()
    updated = 0
    for q in quotas:
        is_full = q.used_storage_bytes >= q.allocated_quota_bytes
        if q.is_full != is_full:
            q.is_full = is_full
            q.save(update_fields=["is_full", "last_calculated_at"])
            updated += 1
    return {"updated": updated}


@shared_task(name="badms.purge_expired_archives")
def purge_expired_archives():
    flagged = (
        ArchivalRequest.objects.filter(
            retention_policy_ref__isnull=False,
        )
        .exclude(retention_policy_ref="")
        .count()
    )
    return {"flagged_for_review": flagged}
