import io

from celery import shared_task


@shared_task(name="badms.execute_backup")
def execute_backup(run_id: int) -> str:
    from modules.badms.services.backups import perform_backup

    run = perform_backup(run_id)
    return f"Backup run {run.pk}: {run.status}"


@shared_task(name="badms.deliver_notifications")
def deliver_notifications(limit: int = 100) -> int:
    from django.core.mail import send_mail
    from django.db import transaction

    from modules.badms.models import NotificationOutbox

    sent = 0
    for row in NotificationOutbox.objects.filter(status="pending").order_by("created_at")[:limit]:
        try:
            count = send_mail(row.subject, row.body, None, [row.recipient], fail_silently=False)
            if count != 1:
                raise RuntimeError("Notification backend accepted no recipients.")  # noqa: TRY301
            with transaction.atomic():
                row.status = "sent"
                row.attempts += 1
                row.save(update_fields=["status", "attempts", "updated_at"])
            sent += 1
        except Exception as exc:  # noqa: BLE001
            row.status = "failed"
            row.attempts += 1
            row.last_error = type(exc).__name__
            row.save(update_fields=["status", "attempts", "last_error", "updated_at"])
    return sent


@shared_task(name="badms.run_due_schedules")
def run_due_schedules() -> int:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from django.utils import timezone

    from modules.badms.models import BackupRun
    from modules.badms.services.backups import effective_schedules
    from modules.badms.services.storage import badms_storage, require_secure_storage

    now = timezone.now()
    try:
        require_secure_storage()
        probe = badms_storage().save("badms/.healthcheck", io.BytesIO(b"ok"))
        badms_storage().delete(probe)
    except Exception:  # noqa: BLE001
        return 0
    count = 0
    for schedule in effective_schedules():
        try:
            local_now = now.astimezone(ZoneInfo(schedule.timezone))
        except (ZoneInfoNotFoundError, ValueError):
            continue
        if (local_now.hour, local_now.minute) != (schedule.scheduled_time.hour,
                                                 schedule.scheduled_time.minute):
            continue
        if schedule.frequency == "weekly" and local_now.weekday() != 0:
            continue
        if schedule.frequency not in ("daily", "weekly"):
            continue
        scheduled_for = local_now.replace(second=0, microsecond=0)
        if BackupRun.objects.filter(dataset=schedule.dataset,
                                    scheduled_for=scheduled_for).exists():
            continue
        run = BackupRun.objects.create(trigger="scheduled", dataset=schedule.dataset,
                                       started_at=now, scheduled_for=scheduled_for)
        execute_backup.delay(run.pk)
        count += 1
    return count


@shared_task(name="badms.monitor_storage_thresholds")
def monitor_storage_thresholds() -> int:
    from django.conf import settings
    from django.db.models import Sum

    from modules.badms.models import ArchiveRequest, AuditEvent, StorageThreshold
    from modules.directory import contracts as directory

    quota = getattr(settings, "BADMS_USER_QUOTA_BYTES", None)
    if not isinstance(quota, int) or quota < 1:
        return 0
    usage_rows = (ArchiveRequest.objects.values("user_id").annotate(
        usage=Sum("attachment_size_bytes")))
    users = directory.get_users([row["user_id"] for row in usage_rows])
    changed = 0
    for row in usage_rows:
        user_id = row["user_id"]
        usage = row["usage"] or 0
        is_full = usage >= quota
        department = users[user_id].department if user_id in users else ""
        current = StorageThreshold.objects.filter(user_id=user_id).first()
        changed_state = current is None or current.is_full != is_full
        threshold, _ = StorageThreshold.objects.update_or_create(
            user_id=user_id,
            defaults={"department": department, "usage_bytes": usage,
                      "quota_bytes": quota, "is_full": is_full})
        if changed_state:
            AuditEvent.objects.create(
                actor_user_id=None, department=department,
                action="storage.threshold_changed", object_type="storage_threshold",
                object_id=str(threshold.pk), outcome="full" if is_full else "available")
            changed += 1
    return changed


@shared_task(name="badms.enforce_retention")
def enforce_retention() -> int:
    from django.utils import timezone

    from modules.badms.models import ArchiveRequest, AuditEvent
    from modules.badms.services.storage import badms_storage

    due = ArchiveRequest.objects.filter(retention_until__lte=timezone.now()).exclude(
        archive_key="")
    removed = 0
    for row in due.iterator():
        keys = {row.archive_key, row.attachment_key} - {""}
        for key in keys:
            badms_storage().delete(key)
        row.archive_key = ""
        row.attachment_key = ""
        row.save(update_fields=["archive_key", "attachment_key", "updated_at"])
        AuditEvent.objects.create(
            actor_user_id=None, department=row.department, action="archive.retention_expired",
            object_type="archive_request", object_id=str(row.pk), outcome="deleted")
        removed += 1
    return removed
