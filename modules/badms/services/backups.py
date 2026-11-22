from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connections, transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.badms.domain.state_machine import transition
from modules.badms.models import BackupRun
from modules.badms.services import audit, notifications, storage

log = logging.getLogger("fusion.badms.backups")


class BackupError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.code = code


def _snapshot_database(run: BackupRun) -> str:
    alias = settings.BADMS_DATASETS.get(run.dataset_key)
    if alias is None:
        raise BackupError("The requested dataset is not configured.",
                          code="dataset_not_configured")
    connection = connections[alias]
    if connection.vendor != "postgresql":
        raise BackupError("BADMS snapshots require PostgreSQL.",
                          code="unsupported_database")
    executable = shutil.which("pg_dump")
    validator = shutil.which("pg_restore")
    if executable is None or validator is None:
        raise BackupError("PostgreSQL backup utilities are unavailable.",
                          code="snapshot_tools_missing")

    database = connection.settings_dict
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as target:
        snapshot_path = target.name
    command = [
        executable,
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        snapshot_path,
    ]
    for option, setting in (
        ("--host", "HOST"),
        ("--port", "PORT"),
        ("--username", "USER"),
    ):
        value = database.get(setting)
        if value:
            command.extend([option, str(value)])
    command.append(str(database["NAME"]))
    environment = os.environ.copy()
    if database.get("PASSWORD"):
        environment["PGPASSWORD"] = str(database["PASSWORD"])
    try:
        subprocess.run(  # noqa: S603 -- system utility is resolved from trusted PATH.
            command,
            check=True,
            capture_output=True,
            timeout=4000,
            env=environment,
        )
        subprocess.run(  # noqa: S603 -- system utility is resolved from trusted PATH.
            [validator, "--list", snapshot_path],
            check=True,
            capture_output=True,
            timeout=300,
            env=environment,
        )
    except FileNotFoundError as exc:
        Path(snapshot_path).unlink(missing_ok=True)
        raise BackupError("PostgreSQL backup utilities are unavailable.",
                          code="snapshot_tools_missing") from exc
    except subprocess.TimeoutExpired as exc:
        Path(snapshot_path).unlink(missing_ok=True)
        raise BackupError("The database snapshot exceeded its time limit.",
                          code="snapshot_timed_out") from exc
    except subprocess.CalledProcessError as exc:
        Path(snapshot_path).unlink(missing_ok=True)
        raise BackupError("PostgreSQL could not create or validate the snapshot.",
                          code="snapshot_failed") from exc
    return snapshot_path


def execute(run_id: int) -> str:
    now = timezone.now()
    with transaction.atomic():
        run = BackupRun.objects.select_for_update().filter(pk=run_id).first()
        if run is None:
            raise NotFoundError("Backup run not found.")
        if run.status in {BackupRun.Status.SUCCEEDED, BackupRun.Status.FAILED}:
            return run.status
        if (run.status == BackupRun.Status.RUNNING and run.started_at
                and run.started_at > now - timedelta(hours=2)):
            return run.status
        if run.status == BackupRun.Status.QUEUED:
            run.status = transition("backup", run.status, "start", "system")
        elif run.status != BackupRun.Status.RUNNING:
            raise BackupError("The backup run has an invalid state.",
                              code="invalid_backup_state")
        run.started_at = now
        run.save(update_fields=["status", "started_at", "updated_at"])
        dataset_key = run.dataset_key
        started_by_user_id = run.started_by_user_id

    snapshot_path = ""
    try:
        snapshot_path = _snapshot_database(run)
        key = (
            f"badms/backups/{dataset_key}/{run.pk}.enc"
        )
        with Path(snapshot_path).open("rb") as snapshot:
            stored = storage.store_stream(
                snapshot,
                key=key,
                owner=f"backup-run:{run_id}",
            )
        with transaction.atomic():
            run = BackupRun.objects.select_for_update().get(pk=run_id)
            run.status = transition("backup", run.status, "succeed", "system")
            run.storage_key = stored.key
            run.checksum_sha256 = stored.sha256
            run.size_bytes = stored.size_bytes
            run.error_code = ""
            run.consecutive_failures = 0
            run.finished_at = timezone.now()
            run.save(update_fields=[
                "status", "storage_key", "checksum_sha256", "size_bytes",
                "error_code", "consecutive_failures", "finished_at", "updated_at",
            ])
        audit.record(
            actor_user_id=started_by_user_id,
            action="backup_succeeded",
            resource="backup",
            resource_id=str(run_id),
            details={"dataset_key": dataset_key, "size_bytes": run.size_bytes},
        )
    except (BackupError, storage.StorageError) as exc:
        with transaction.atomic():
            run = BackupRun.objects.select_for_update().get(pk=run_id)
            run.status = transition("backup", run.status, "fail", "system")
            previous = (
                BackupRun.objects.filter(
                    dataset_key=dataset_key,
                    finished_at__isnull=False,
                )
                .exclude(pk=run_id)
                .order_by("-finished_at")
                .first()
            )
            run.consecutive_failures = (
                previous.consecutive_failures + 1
                if previous and previous.status == BackupRun.Status.FAILED
                else 1
            )
            run.error_code = exc.code
            run.finished_at = timezone.now()
            run.save(update_fields=[
                "status", "consecutive_failures", "error_code",
                "finished_at", "updated_at",
            ])
        audit.record(
            actor_user_id=started_by_user_id,
            action="backup_failed",
            resource="backup",
            resource_id=str(run_id),
            outcome="failure",
            details={"error_code": run.error_code, "dataset_key": dataset_key},
        )
        notifications.enqueue_emails(
            recipients=settings.BADMS_SYSADMIN_EMAILS,
            subject="BADMS backup failed",
            body=(
                f"Backup run {run_id} for {dataset_key} failed with "
                f"{run.error_code} at {run.finished_at.isoformat()}."
            ),
            resource="backup",
            resource_id=str(run_id),
        )
        if run.consecutive_failures == 3:
            notifications.enqueue_emails(
                recipients=settings.BADMS_IT_DIRECTOR_EMAILS,
                subject="BADMS backup escalation",
                body=(
                    f"Three consecutive backups failed for {dataset_key}. "
                    f"The latest run is {run_id}; error code {run.error_code}."
                ),
                resource="backup",
                resource_id=str(run_id),
            )
        log.error("badms.backup.failed run_id=%s error_code=%s",
                  run_id, run.error_code)
        return run.status
    else:
        return run.status
    finally:
        if snapshot_path:
            Path(snapshot_path).unlink(missing_ok=True)
