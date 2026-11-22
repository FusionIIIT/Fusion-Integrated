import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.badms.models import AuditEvent, BackupRun, BackupSchedule, NotificationOutbox
from modules.badms.services import notifications
from modules.badms.services.storage import badms_storage, require_secure_storage


def queue_manual(*, actor, dataset: str = "fusionlab") -> BackupRun:
    require_secure_storage()
    run = BackupRun.objects.create(trigger="manual", dataset=dataset,
                                   actor_user_id=actor.user_id,
                                   actor_email=getattr(actor, "email", ""),
                                   started_at=timezone.now())
    from modules.badms.tasks import execute_backup

    execute_backup.delay(run.pk)
    return run


def perform_backup(run_id: int) -> BackupRun:
    storage = badms_storage()
    run = BackupRun.objects.get(pk=run_id)
    try:
        require_secure_storage()
        db = settings.DATABASES["default"]
        if "postgresql" not in db["ENGINE"]:
            raise ConflictError(  # noqa: TRY301
                "BADMS backups require a PostgreSQL database.", code="unsupported_database")
        name = db.get("NAME")
        if not name:
            raise ConflictError(  # noqa: TRY301
                "The database name is not configured.", code="database_not_configured")
        pg_dump = shutil.which("pg_dump")
        if not pg_dump:
            raise ConflictError(  # noqa: TRY301
                "The PostgreSQL dump utility is unavailable.", code="pg_dump_unavailable")
        pg_env = os.environ.copy()
        for setting, variable in (("HOST", "PGHOST"), ("PORT", "PGPORT"),
                                  ("USER", "PGUSER"), ("PASSWORD", "PGPASSWORD")):
            value = db.get(setting)
            if value:
                pg_env[variable] = str(value)
        with tempfile.TemporaryDirectory(prefix="badms-") as temp_dir:
            dump_path = Path(temp_dir) / "database.dump"
            result = subprocess.run(  # noqa: S603
                [pg_dump, "--format=custom", "--no-owner", "--no-privileges",
                 "--file", str(dump_path), str(name)],
                env=pg_env, capture_output=True, text=True, timeout=3600, check=False)
            if result.returncode:
                raise RuntimeError("Database dump failed.")  # noqa: TRY301
            digest = hashlib.sha256()
            with dump_path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
            key = f"badms/recovery/{run.dataset}/{stamp}-{run.pk}.dump"
            with dump_path.open("rb") as source:
                artifact_key = storage.save(key, File(source))
        run.status = "success"
        run.completed_at = timezone.now()
        run.artifact_key = artifact_key
        run.checksum_sha256 = digest.hexdigest()
        check = hashlib.sha256()
        if storage.exists(artifact_key):
            with storage.open(artifact_key, "rb") as saved:
                for chunk in iter(lambda: saved.read(1024 * 1024), b""):
                    check.update(chunk)
        run.integrity_verified = check.hexdigest() == digest.hexdigest()
        run.outcome = "Database dump saved; SHA-256 checksum recorded."
        if not run.integrity_verified:
            raise RuntimeError("Saved backup checksum verification failed.")  # noqa: TRY301
        run.save(update_fields=["status", "completed_at", "artifact_key",
                                "checksum_sha256", "integrity_verified", "outcome",
                                "updated_at"])
        _record_outcome(run, "success")
        notifications.enqueue([run.actor_email], subject="BADMS backup completed",
                              body=f"Backup run {run.pk} for {run.dataset} completed.")
    except Exception as exc:  # noqa: BLE001
        run.status = "failure"
        run.completed_at = timezone.now()
        run.integrity_verified = False
        run.outcome = "Backup failed; see operational logs for request ID."
        run.save(update_fields=["status", "completed_at", "integrity_verified",
                                "outcome", "updated_at"])
        _record_outcome(run, "failure", detail=type(exc).__name__)
        _queue_failure_alerts(run)
    return run


@transaction.atomic
def _record_outcome(run: BackupRun, outcome: str, detail: str = "") -> None:
    AuditEvent.objects.create(actor_user_id=run.actor_user_id,
                              action=f"backup.{outcome}", object_type="backup_run",
                              object_id=str(run.pk), outcome=outcome,
                              details={"dataset": run.dataset, "detail": detail})


def _queue_failure_alerts(run: BackupRun) -> None:
    recipients = [x.strip() for x in getattr(settings, "BADMS_SYSADMIN_ALERT_EMAILS", [])
                  if x.strip()]
    failures = list(BackupRun.objects.filter(dataset=run.dataset)
                    .order_by("-started_at").values_list("status", flat=True)[:3])
    director = getattr(settings, "BADMS_DIRECTOR_ALERT_EMAIL", "")
    if failures == ["failure"] * 3 and director:
        recipients.append(director)
    for recipient in set(recipients):
        NotificationOutbox.objects.create(
            recipient=recipient, subject="BADMS backup failure",
            body=f"Backup run {run.pk} for {run.dataset} failed. Outcome: {run.outcome}")


def effective_schedules():
    local = list(BackupSchedule.objects.filter(scope="local", enabled=True))
    local_datasets = {row.dataset for row in local}
    global_rows = BackupSchedule.objects.filter(scope="global", enabled=True)
    return [*local, *(row for row in global_rows if row.dataset not in local_datasets)]
