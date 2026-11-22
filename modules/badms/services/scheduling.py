from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from celery.schedules import crontab
from django.db import transaction
from django.utils import timezone

from modules.badms.domain.scheduling import effective_schedules
from modules.badms.models import BackupRun, BackupSchedule
from modules.badms.tasks import run_backup


def _cron(schedule: BackupSchedule) -> crontab:
    fields = schedule.cron_expression.split()
    if len(fields) != 5:
        raise ValueError(f"Invalid cron expression for schedule {schedule.pk}.")
    try:
        zone = ZoneInfo(schedule.timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Invalid timezone for schedule {schedule.pk}.") from exc
    return crontab(
        minute=fields[0],
        hour=fields[1],
        day_of_month=fields[2],
        month_of_year=fields[3],
        day_of_week=fields[4],
        nowfun=lambda: timezone.now().astimezone(zone),
    )


@transaction.atomic
def _queue_if_due(schedule: BackupSchedule) -> bool:
    schedule = BackupSchedule.objects.select_for_update().get(pk=schedule.pk)
    latest = (
        BackupRun.objects.select_for_update()
        .filter(schedule=schedule)
        .order_by("-created_at")
        .first()
    )
    last_run = latest.created_at if latest else schedule.created_at
    if not _cron(schedule).is_due(last_run).is_due:
        return False
    run = BackupRun.objects.create(
        dataset_key=schedule.dataset_key,
        trigger=BackupRun.Trigger.SCHEDULED,
        schedule=schedule,
    )
    transaction.on_commit(lambda: run_backup.delay(run.pk))
    return True


def dispatch_due() -> int:
    schedules = BackupSchedule.objects.filter(enabled=True).order_by("pk")
    return sum(
        _queue_if_due(schedule)
        for schedule in effective_schedules(schedules)
    )
