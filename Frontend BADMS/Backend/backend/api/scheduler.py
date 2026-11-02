import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

_scheduler = None


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_jobstore(DjangoJobStore(), "default")
    return _scheduler


# ── job ────────────────────────────────────────────────────────────────────────


def _do_backup(db_name: str, schedule_id: str):
    """
    The actual job function called by APScheduler.
    Runs pg_dump synchronously (already in a background thread via APScheduler)
    and updates the BackupSchedule last_run_at / next_run_at.
    Also enforces the retain_last_n policy.
    """
    # Import here to avoid circular imports at module load time
    import os
    import subprocess

    from .views.backups import (
        MAIN_DB_ALIAS,
        _alias_for_db_name,
        _dump_path,
        _encrypt_file_in_place,
        _get_db_config,
        _get_fernet,
        _pg_env,
    )
    from .models import BackupRecord, BackupSchedule

    logger.info("Scheduled backup starting for db=%s", db_name)

    # Dump the database this schedule targets (main ERP or system), using that
    # database's own credentials — not always the default connection.
    alias = _alias_for_db_name(db_name) or MAIN_DB_ALIAS
    cfg = _get_db_config(alias)
    record = BackupRecord.objects.create(db_name=db_name, status="in_progress")
    dump_path = _dump_path(db_name, record.id, record.created_at)

    cmd = [
        "pg_dump",
        "-h",
        cfg["host"],
        "-p",
        cfg["port"],
        "-U",
        cfg["user"],
        "-Fc",
        "-f",
        dump_path,
        db_name,
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            env=_pg_env(cfg),
            capture_output=True,
            text=True,
            timeout=600,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            record.status = "failed"
            record.error_message = result.stderr[:2000]
            record.duration_ms = elapsed_ms
            record.save()
            logger.error(
                "Scheduled backup FAILED for %s: %s", db_name, result.stderr[:200]
            )
        else:
            fernet = _get_fernet()
            if fernet:
                _encrypt_file_in_place(dump_path, fernet)
                record.encrypted = True
            file_size = os.path.getsize(dump_path) if os.path.exists(dump_path) else 0
            record.status = "success"
            record.duration_ms = elapsed_ms
            record.size_bytes = file_size
            record.file_path = dump_path
            record.save()
            logger.info(
                "Scheduled backup OK for %s — %d bytes in %dms",
                db_name,
                file_size,
                elapsed_ms,
            )
            # enforce retention policy
            _enforce_retention(db_name, schedule_id)

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start) * 1000)
        record.status = "failed"
        record.error_message = "Backup timed out after 10 minutes."
        record.duration_ms = elapsed_ms
        record.save()
        logger.error("Scheduled backup TIMED OUT for %s", db_name)
    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        record.status = "failed"
        record.error_message = str(exc)[:2000]
        record.duration_ms = elapsed_ms
        record.save()
        logger.exception("Scheduled backup EXCEPTION for %s", db_name)

    # update last_run_at on the schedule
    try:
        sched = BackupSchedule.objects.get(id=schedule_id)
        sched.last_run_at = timezone.now()
        # compute next_run_at from APScheduler job
        scheduler = get_scheduler()
        job_id = _job_id(db_name)
        job = scheduler.get_job(job_id)
        if job and job.next_run_time:
            sched.next_run_at = job.next_run_time
        sched.save(update_fields=["last_run_at", "next_run_at"])
    except Exception:
        pass


def _enforce_retention(db_name: str, schedule_id: str):
    """Delete old successful backups beyond retain_last_n."""
    import os

    from .models import BackupRecord, BackupSchedule

    try:
        sched = BackupSchedule.objects.get(id=schedule_id)
        n = sched.retain_last_n
        if n <= 0:
            return
        # get all successful backups ordered newest first
        successful = BackupRecord.objects.filter(
            db_name=db_name, status="success"
        ).order_by("-created_at")
        to_delete = successful[n:]
        for b in to_delete:
            if b.file_path and os.path.exists(b.file_path):
                try:
                    os.remove(b.file_path)
                except OSError:
                    pass
            b.delete()
            logger.info("Retention: deleted old backup %s for %s", b.id, db_name)
    except Exception:
        logger.exception("Retention enforcement failed for %s", db_name)


# ── helpers ────────────────────────────────────────────────────────────────────


def _job_id(db_name: str) -> str:
    return f"backup_{db_name}"


def _build_trigger(schedule) -> CronTrigger:
    """Build a CronTrigger from a BackupSchedule instance."""
    if schedule.frequency == "custom" and schedule.cron_expression:
        parts = schedule.cron_expression.strip().split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            return CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone="UTC",
            )
        else:
            raise ValueError(
                f"Invalid cron expression '{schedule.cron_expression}'. "
                "Expected 5 fields: minute hour day month weekday"
            )

    if schedule.frequency == "daily":
        return CronTrigger(
            hour=schedule.hour,
            minute=schedule.minute,
            timezone="UTC",
        )

    if schedule.frequency == "weekly":
        dow = schedule.day_of_week if schedule.day_of_week is not None else 0
        return CronTrigger(
            day_of_week=dow,
            hour=schedule.hour,
            minute=schedule.minute,
            timezone="UTC",
        )

    if schedule.frequency == "monthly":
        dom = schedule.day_of_month if schedule.day_of_month is not None else 1
        return CronTrigger(
            day=dom,
            hour=schedule.hour,
            minute=schedule.minute,
            timezone="UTC",
        )

    raise ValueError(f"Unknown frequency: {schedule.frequency}")


def register_schedule(schedule):
    """
    Add or replace the APScheduler job for this BackupSchedule.
    Safe to call multiple times (replaces existing job).
    """
    from .models import BackupSchedule

    scheduler = get_scheduler()
    job_id = _job_id(schedule.db_name)

    if not schedule.enabled:
        deregister_schedule(schedule.db_name)
        return

    trigger = _build_trigger(schedule)

    scheduler.add_job(
        _do_backup,
        trigger=trigger,
        id=job_id,
        name=f"Backup {schedule.db_name}",
        kwargs={"db_name": schedule.db_name, "schedule_id": str(schedule.id)},
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1h late firing
    )

    # update next_run_at immediately
    try:
        job = scheduler.get_job(job_id)
        if job and job.next_run_time:
            schedule.next_run_at = job.next_run_time
            schedule.save(update_fields=["next_run_at"])
    except Exception:
        pass

    logger.info("Registered scheduled backup job: %s", job_id)


def deregister_schedule(db_name: str):
    """Remove the APScheduler job for this db, if it exists."""
    scheduler = get_scheduler()
    job_id = _job_id(db_name)
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info("Removed scheduled backup job: %s", job_id)
    except Exception:
        pass


def start():
    """
    Start the scheduler and re-register all active BackupSchedules from the DB.
    Called once from AppConfig.ready().
    """
    from .models import BackupSchedule

    scheduler = get_scheduler()

    if scheduler.running:
        return

    scheduler.start()
    logger.info("APScheduler started.")

    # re-register all enabled schedules
    for sched in BackupSchedule.objects.filter(enabled=True):
        try:
            register_schedule(sched)
        except Exception:
            logger.exception("Failed to register schedule for %s", sched.db_name)
