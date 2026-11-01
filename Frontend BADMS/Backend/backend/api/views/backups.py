import os
import re
import subprocess
import threading
import time
import uuid as _uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection, connections
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from ..models import BackupRecord, BackupSchedule, HealthCheck, RestoreRecord

# ── config ──────────────────────────────────────────────────────────────────────

BACKUP_DIR = Path(settings.BASE_DIR) / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# ── database targets ─────────────────────────────────────────────────────────────
#
# This tool manages two PostgreSQL databases (see backend.routers.SystemDBRouter):
#
#   * "default"   — the main Fusion ERP database. Its name is environment-specific:
#                   'fusionlab' in development and 'fusion_newui_prod' in production
#                   (driven by DB_NAME in .env). This is the ONLY database we ever
#                   restore into.
#   * "system_db" — this admin tool's own database (operator logins, backup/restore
#                   history, schedules, health checks).
#
# BOTH databases are backed up. Restore, however, is deliberately limited to the ERP
# database: restoring "system_db" would drop and recreate the auth/backup tables that
# the running server is actively using, crashing the process mid-restore and wiping
# the very audit trail we depend on. So the system database is backup-only.
MAIN_DB_ALIAS = "default"
SYSTEM_DB_ALIAS = "system_db"

# Aliases included when backing up "everything" (both databases).
BACKUP_DB_ALIASES = (MAIN_DB_ALIAS, SYSTEM_DB_ALIAS)

# Recognised names of the main ERP database across environments. A backup may only be
# restored if its db_name is one of these — never the system database.
RESTORABLE_DB_NAMES = {"fusionlab", "fusion_newui_prod"}


def _get_db_config(db_alias="default"):
    """Pull the database credentials from Django settings for the given alias."""
    db = settings.DATABASES[db_alias]
    return {
        "name": db["NAME"],
        "user": db["USER"],
        "password": db["PASSWORD"],
        "host": db.get("HOST", "localhost"),
        "port": db.get("PORT", "5432"),
    }


def _db_name_for_alias(db_alias):
    """Return the configured database NAME for a settings alias."""
    return settings.DATABASES[db_alias]["NAME"]


def _alias_for_db_name(db_name):
    """Resolve a database name back to its settings alias, or None if not configured.

    Lets backup/health operations use the correct connection credentials for whichever
    database was requested, instead of always assuming the "default" alias.
    """
    for alias, cfg in settings.DATABASES.items():
        if cfg.get("NAME") == db_name:
            return alias
    return None


def _is_restorable(db_name):
    """Whether a backup of ``db_name`` may be restored.

    Only the main Fusion ERP database (fusionlab / fusion_newui_prod) is restorable.
    The system database is explicitly excluded — see the note above.
    """
    if db_name == _db_name_for_alias(SYSTEM_DB_ALIAS):
        return False
    return db_name in RESTORABLE_DB_NAMES


# Dump files are named "<db_name>__<YYYY-MM-DD_HH-MM-SS>__<uuid>.dump" so they are
# human-readable AND self-describing: at a glance you can see which database it holds
# and when it was taken, without opening the BackupRecord. The timestamp is UTC (the
# app runs in UTC). The trailing UUID guarantees uniqueness and links the file back to
# its record. Fields are joined by "__"; db names use single underscores and the
# timestamp/UUID contain none, so the fields are recovered by splitting on "__" (the
# UUID is always the last field). Legacy names still recognised for back-compat:
#   "<db>__<uuid>.dump"  and  "<uuid>.dump"  (no db prefix -> assumed main ERP db).
_DUMP_SUFFIX = ".dump"
_DUMP_SEP = "__"
_DUMP_TS_FORMAT = "%Y-%m-%d_%H-%M-%S"
_UNSAFE_DB_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


def _safe_db(db_name):
    """Sanitise a db name for use as a path segment / filename part."""
    return _UNSAFE_DB_CHARS.sub("_", db_name)


def _dump_dir(db_name):
    """Return (creating if needed) the per-database backup sub-folder.

    Each database gets its own folder under ``backups/`` — e.g.
    ``backups/fusionlab/`` (or ``backups/fusion_newui_prod/`` in prod) and
    ``backups/fusion_system_db/`` — so the main ERP and system-DB dumps are never
    mixed together on disk.
    """
    d = BACKUP_DIR / _safe_db(db_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dump_filename(db_name, record_id, created_at):
    """Build the on-disk dump filename for a backup record.

    ``created_at`` is the record's timezone-aware creation time; it is rendered in UTC
    so the on-disk name matches the timestamp stored in the database.
    """
    stamp = timezone.localtime(created_at, timezone.utc).strftime(_DUMP_TS_FORMAT)
    return f"{_safe_db(db_name)}{_DUMP_SEP}{stamp}{_DUMP_SEP}{record_id}{_DUMP_SUFFIX}"


def _dump_path(db_name, record_id, created_at):
    """Full path to a backup dump: ``backups/<db_name>/<db>__<ts>__<uuid>.dump``."""
    return str(_dump_dir(db_name) / _dump_filename(db_name, record_id, created_at))


def _parse_dump_filename(stem):
    """Parse a dump filename stem (name without ``.dump``) into (db_name, uuid_str).

    Handles all three name shapes — "<db>__<ts>__<uuid>", "<db>__<uuid>", and legacy
    "<uuid>". The UUID is always the last "__"-separated field and the db name (if any)
    is the first. The timestamp field is purely cosmetic and ignored here (the record's
    created_at is authoritative). Returns db_name=None when there is no db prefix, and
    (None, None) if the last field is not a valid UUID.
    """
    parts = stem.split(_DUMP_SEP)
    uuid_part = parts[-1]
    try:
        _uuid.UUID(uuid_part)
    except ValueError:
        return None, None
    db_part = parts[0] if len(parts) >= 2 else None
    return (db_part or None), uuid_part


def _pg_env(cfg):
    """Return a copy of os.environ with PGPASSWORD set."""
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg["password"]
    return env


# ── at-rest encryption (optional) ────────────────────────────────────────────────
#
# When settings.BACKUP_ENCRYPTION_KEY is set, dump files are Fernet-encrypted on disk
# (AES-128-CBC + HMAC) and decrypted to a short-lived temp file only during restore.
# With no key, backups are plain pg_dump output (unchanged behaviour). Encryption
# state is recorded per-backup (BackupRecord.encrypted) so restore knows what to do.


def _get_fernet():
    """Return a Fernet cipher if backup encryption is configured, else None."""
    key = getattr(settings, "BACKUP_ENCRYPTION_KEY", "")
    if not key:
        return None
    from cryptography.fernet import Fernet

    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt_file_in_place(path, fernet):
    """Replace a file's contents with their Fernet-encrypted form."""
    with open(path, "rb") as fh:
        data = fh.read()
    with open(path, "wb") as fh:
        fh.write(fernet.encrypt(data))


def _decrypt_to_tempfile(path, fernet):
    """Decrypt an encrypted dump into a temp file; returns its path (caller deletes)."""
    import tempfile

    with open(path, "rb") as fh:
        plaintext = fernet.decrypt(fh.read())
    fd, tmp = tempfile.mkstemp(suffix=".dump", dir=str(BACKUP_DIR))
    with os.fdopen(fd, "wb") as fh:
        fh.write(plaintext)
    return tmp


# ── helpers ─────────────────────────────────────────────────────────────────────


def _run_backup(record_id):
    """Run pg_dump in a background thread and update the BackupRecord."""
    record = BackupRecord.objects.get(id=record_id)
    # Use the credentials of whichever database this record targets (main ERP or
    # system), falling back to the main DB for orphaned/unknown names.
    alias = _alias_for_db_name(record.db_name) or MAIN_DB_ALIAS
    cfg = _get_db_config(alias)
    dump_path = _dump_path(record.db_name, record.id, record.created_at)

    cmd = [
        "pg_dump",
        "-h",
        cfg["host"],
        "-p",
        cfg["port"],
        "-U",
        cfg["user"],
        "-Fc",  # custom format, needed for pg_restore
        "-f",
        dump_path,
        record.db_name,
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            env=_pg_env(cfg),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute safety timeout
        )
        elapsed_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            record.status = "failed"
            record.error_message = result.stderr[:2000]
            record.duration_ms = elapsed_ms
            record.save()
            return

        # Encrypt at rest if configured (before we record size, so it reflects the
        # encrypted file that actually sits on disk).
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

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start) * 1000)
        record.status = "failed"
        record.error_message = "Backup timed out after 10 minutes."
        record.duration_ms = elapsed_ms
        record.save()
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        record.status = "failed"
        record.error_message = str(e)[:2000]
        record.duration_ms = elapsed_ms
        record.save()


def _run_restore(dump_path, restore_record_id, encrypted=False):
    """
    Run pg_restore in a background thread and update the RestoreRecord.

    Restore always targets the main ERP database (the "default" alias — fusionlab in
    dev, fusion_newui_prod in prod). The system database is never a restore target;
    the restore_backup endpoint rejects it before we ever get here.

    If the dump is encrypted at rest, it is decrypted to a short-lived temp file that
    pg_restore reads and which is deleted in the `finally` below.
    """
    cfg = _get_db_config(MAIN_DB_ALIAS)

    restore_source = dump_path
    temp_source = None
    if encrypted:
        fernet = _get_fernet()
        if fernet is None:
            record = RestoreRecord.objects.get(id=restore_record_id)
            record.status = "failed"
            record.error_message = (
                "Backup is encrypted but BACKUP_ENCRYPTION_KEY is not configured."
            )
            record.finished_at = timezone.now()
            record.save()
            return
        temp_source = _decrypt_to_tempfile(dump_path, fernet)
        restore_source = temp_source

    cmd = [
        "pg_restore",
        "-h",
        cfg["host"],
        "-p",
        cfg["port"],
        "-U",
        cfg["user"],
        "-d",
        cfg["name"],
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        restore_source,
    ]

    start = time.time()
    try:
        record = RestoreRecord.objects.get(id=restore_record_id)
        result = subprocess.run(
            cmd,
            env=_pg_env(cfg),
            capture_output=True,
            text=True,
            timeout=600,
        )
        elapsed_ms = int((time.time() - start) * 1000)
        record.duration_ms = elapsed_ms
        record.finished_at = timezone.now()

        if result.returncode != 0:
            record.status = "failed"
            stderr_message = (result.stderr or "").strip()
            if stderr_message:
                record.error_message = stderr_message[:2000]
            else:
                record.error_message = (
                    f"pg_restore failed with exit code {result.returncode}."
                )
        else:
            record.status = "success"
            record.error_message = ""
        record.save()
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - start) * 1000)
        try:
            record = RestoreRecord.objects.get(id=restore_record_id)
            record.status = "failed"
            record.error_message = "Restore timed out after 10 minutes."
            record.duration_ms = elapsed_ms
            record.finished_at = timezone.now()
            record.save()
        except Exception:
            pass
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        try:
            record = RestoreRecord.objects.get(id=restore_record_id)
            record.status = "failed"
            record.error_message = str(e)[:2000]
            record.duration_ms = elapsed_ms
            record.finished_at = timezone.now()
            record.save()
        except Exception:
            pass
    finally:
        # never leave a decrypted plaintext dump lying around
        if temp_source and os.path.exists(temp_source):
            try:
                os.remove(temp_source)
            except OSError:
                pass


# ── views ───────────────────────────────────────────────────────────────────────


def _sync_orphaned_backups():
    """
    Scan the backup folder for .dump files that have no matching
    BackupRecord and create records for them so they appear in the UI.

    The database is read from the filename ("<db>__<uuid>.dump"). Legacy files
    without a db prefix fall back to the main ERP database name.

    Security: Only .dump files are expected. Unexpected files are logged as warnings.
    """
    existing_ids = set(
        str(pk) for pk in BackupRecord.objects.values_list("id", flat=True)
    )

    # Recurse: dumps now live in per-database sub-folders (older ones may still sit
    # flat in the root), so scan the whole tree.
    for dump_file in BACKUP_DIR.rglob(f"*{_DUMP_SUFFIX}"):
        try:
            # Reject broken symlinks — should not exist in backup directory
            if not dump_file.exists():
                logger.warning(f"Broken symlink or inaccessible file in backup dir: {dump_file}")
                continue

            db_name, file_uuid = _parse_dump_filename(dump_file.stem)
            if file_uuid is None:  # not a recognisable dump file
                logger.warning(f"File in backup dir with invalid dump name format: {dump_file}")
                continue
            if file_uuid in existing_ids:
                continue

            # legacy files carry no db prefix; assume the main ERP database
            if db_name is None:
                db_name = _db_name_for_alias(MAIN_DB_ALIAS)

            parsed = _uuid.UUID(file_uuid)
            file_size = dump_file.stat().st_size
            file_mtime = timezone.datetime.fromtimestamp(
                dump_file.stat().st_mtime, tz=timezone.utc
            )

            BackupRecord.objects.create(
                id=parsed,
                db_name=db_name,
                status="success",
                size_bytes=file_size,
                file_path=str(dump_file),
            )
            # auto_now_add ignores values passed to create(), so update directly
            BackupRecord.objects.filter(id=parsed).update(created_at=file_mtime)
        except (OSError, PermissionError) as e:
            # Permission errors should alert admins — this may indicate a security issue
            logger.error(f"Permission denied accessing backup file (check directory permissions): {dump_file} — {e}")
            continue


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_backups(request):
    """List all backup records, optionally filtered by db_name."""
    # sync orphaned dump files from the backup folder into the DB
    _sync_orphaned_backups()

    db_name = request.GET.get("db_name")
    qs = BackupRecord.objects.all()
    if db_name:
        qs = qs.filter(db_name=db_name)

    data = []
    for b in qs:
        data.append(
            {
                "id": str(b.id),
                "db_name": b.db_name,
                "created_at": b.created_at.isoformat(),
                "status": b.status,
                "size_bytes": b.size_bytes,
                "duration_ms": b.duration_ms,
                "file_name": Path(b.file_path).name if b.file_path else None,
                "error_message": b.error_message,
                "encrypted": b.encrypted,
            }
        )

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_backup(request):
    """
    Kick off a new pg_dump backup in a background thread.
    Returns the backup record immediately with status 'in_progress'.

    Either database may be backed up: pass ``db_name`` for the main ERP or the system
    database. When omitted, the main ERP database is used. Unknown names are rejected
    so we never spawn a pg_dump against a database that isn't configured.
    """
    db_name = request.data.get("db_name") or _db_name_for_alias(MAIN_DB_ALIAS)

    if _alias_for_db_name(db_name) is None:
        return Response(
            {"error": f"Unknown database '{db_name}'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    record = BackupRecord.objects.create(
        db_name=db_name,
        status="in_progress",
    )

    thread = threading.Thread(target=_run_backup, args=(record.id,), daemon=True)
    thread.start()

    return Response(
        {
            "id": str(record.id),
            "db_name": record.db_name,
            "created_at": record.created_at.isoformat(),
            "status": record.status,
            "size_bytes": record.size_bytes,
            "duration_ms": record.duration_ms,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_backup(request, backup_id):
    """Get a single backup record by ID (used for polling status)."""
    try:
        b = BackupRecord.objects.get(id=backup_id)
    except BackupRecord.DoesNotExist:
        return Response(
            {"error": "Backup not found."}, status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        {
            "id": str(b.id),
            "db_name": b.db_name,
            "created_at": b.created_at.isoformat(),
            "status": b.status,
            "size_bytes": b.size_bytes,
            "duration_ms": b.duration_ms,
            "file_path": b.file_path,
            "error_message": b.error_message,
        }
    )


@api_view(["DELETE"])
@permission_classes([IsAdminUser])  # destructive: deletes a backup + its dump file
def delete_backup(request, backup_id):
    """Delete a backup record and its dump file from disk."""
    try:
        b = BackupRecord.objects.get(id=backup_id)
    except BackupRecord.DoesNotExist:
        return Response(
            {"error": "Backup not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if b.status == "in_progress":
        return Response(
            {"error": "Cannot delete an in-progress backup."},
            status=status.HTTP_409_CONFLICT,
        )

    # remove file from disk
    if b.file_path and os.path.exists(b.file_path):
        try:
            os.remove(b.file_path)
        except OSError:
            pass

    b.delete()
    return Response({"message": "Backup deleted."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAdminUser])  # destructive: overwrites the entire ERP DB
def restore_backup(request, backup_id):
    """
    Restore the database from a backup.
    Kicks off pg_restore in a background thread and returns immediately.
    Creates a RestoreRecord to track progress.
    """
    try:
        b = BackupRecord.objects.get(id=backup_id)
    except BackupRecord.DoesNotExist:
        return Response(
            {"error": "Backup not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Guard: only the main ERP database may be restored. Restoring the system database
    # would drop the auth/backup tables this server is running on and crash it, so we
    # reject it here before any pg_restore is started.
    if not _is_restorable(b.db_name):
        return Response(
            {
                "error": (
                    f"'{b.db_name}' cannot be restored. Only the main Fusion ERP "
                    f"database is restorable; the system database is backup-only."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if b.status != "success":
        return Response(
            {"error": "Can only restore from a successful backup."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not b.file_path or not os.path.exists(b.file_path):
        return Response(
            {"error": "Backup file not found on disk."},
            status=status.HTTP_404_NOT_FOUND,
        )

    restore_record = RestoreRecord.objects.create(
        db_name=b.db_name,
        source_backup=b,
        source_backup_created_at=b.created_at,
        status="in_progress",
    )

    thread = threading.Thread(
        target=_run_restore,
        args=(b.file_path, restore_record.id, b.encrypted),
        daemon=True,
    )
    thread.start()

    return Response(
        {
            "restore_id": str(restore_record.id),
            "backup_id": str(b.id),
            "db_name": restore_record.db_name,
            "started_at": restore_record.started_at.isoformat(),
            "status": restore_record.status,
            "source_backup_created_at": b.created_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_restore(request, restore_id):
    """Poll a single restore record by ID."""
    try:
        r = RestoreRecord.objects.get(id=restore_id)
    except RestoreRecord.DoesNotExist:
        return Response(
            {"error": "Restore record not found."}, status=status.HTTP_404_NOT_FOUND
        )

    return Response(_serialize_restore(r))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_restores(request):
    """List restore records, optionally filtered by db_name."""
    db_name = request.GET.get("db_name")
    qs = RestoreRecord.objects.all()
    if db_name:
        qs = qs.filter(db_name=db_name)

    return Response([_serialize_restore(r) for r in qs])


def _serialize_restore(r):
    return {
        "id": str(r.id),
        "db_name": r.db_name,
        "source_backup_id": str(r.source_backup_id) if r.source_backup_id else None,
        "source_backup_created_at": r.source_backup_created_at.isoformat()
        if r.source_backup_created_at
        else None,
        "started_at": r.started_at.isoformat(),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "status": r.status,
        "duration_ms": r.duration_ms,
        "error_message": r.error_message,
    }


# ── health checks ──────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_health_checks(request):
    """
    Return health check records for the last 90 days.
    Optionally filtered by db_name.
    Returns matching rows as stored (not grouped/padded by day).
    """
    db_name = request.GET.get("db_name", _get_db_config()["name"])
    since = timezone.now() - timedelta(days=90)
    qs = HealthCheck.objects.filter(db_name=db_name, checked_at__gte=since)

    data = []
    for h in qs:
        data.append(
            {
                "id": str(h.id),
                "db_name": h.db_name,
                "checked_at": h.checked_at.isoformat(),
                "status": h.status,
                "response_time_ms": h.response_time_ms,
                "error_message": h.error_message,
            }
        )

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_health_check(request):
    """
    Run a health check right now: ping the database and record the result.
    """
    db_name = request.data.get("db_name") or _db_name_for_alias(MAIN_DB_ALIAS)
    # Ping the connection that actually backs this db_name (main ERP or system),
    # falling back to the main DB for unknown names.
    alias = _alias_for_db_name(db_name) or MAIN_DB_ALIAS

    start = time.time()
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT 1")
        elapsed_ms = int((time.time() - start) * 1000)

        record = HealthCheck.objects.create(
            db_name=db_name,
            status="success",
            response_time_ms=elapsed_ms,
        )
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        record = HealthCheck.objects.create(
            db_name=db_name,
            status="failed",
            response_time_ms=elapsed_ms,
            error_message=str(e)[:2000],
        )

    return Response(
        {
            "id": str(record.id),
            "db_name": record.db_name,
            "checked_at": record.checked_at.isoformat(),
            "status": record.status,
            "response_time_ms": record.response_time_ms,
            "error_message": record.error_message,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_schedules(request):
    """List all backup schedules."""
    schedules = BackupSchedule.objects.all()
    return Response([_serialize_schedule(s) for s in schedules])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_schedule(request):
    """
    Create or update a BackupSchedule for a given db_name.
    If one already exists for that db_name, it is updated.
    """
    from .. import scheduler as sched_module

    db_name = request.data.get("db_name")
    if not db_name:
        return Response(
            {"error": "db_name is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    frequency = request.data.get("frequency", "daily")
    enabled = request.data.get("enabled", True)
    hour = int(request.data.get("hour", 2))
    minute = int(request.data.get("minute", 0))
    day_of_week = request.data.get("day_of_week")
    day_of_month = request.data.get("day_of_month")
    cron_expression = request.data.get("cron_expression", "")
    retain_last_n = int(request.data.get("retain_last_n", 7))

    if day_of_week is not None:
        day_of_week = int(day_of_week)
    if day_of_month is not None:
        day_of_month = int(day_of_month)

    # validate cron expression if custom
    if frequency == "custom" and cron_expression:
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return Response(
                {
                    "error": "Custom cron expression must have exactly 5 fields: minute hour day month weekday."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    sched, created = BackupSchedule.objects.update_or_create(
        db_name=db_name,
        defaults={
            "frequency": frequency,
            "enabled": enabled,
            "hour": hour,
            "minute": minute,
            "day_of_week": day_of_week,
            "day_of_month": day_of_month,
            "cron_expression": cron_expression,
            "retain_last_n": retain_last_n,
        },
    )

    # register / update the APScheduler job
    try:
        sched_module.register_schedule(sched)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": f"Schedule saved but failed to register job: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    sched.refresh_from_db()
    return Response(
        _serialize_schedule(sched),
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_schedule(request, schedule_id):
    """Enable or disable a schedule without deleting it."""
    from .. import scheduler as sched_module

    try:
        sched = BackupSchedule.objects.get(id=schedule_id)
    except BackupSchedule.DoesNotExist:
        return Response(
            {"error": "Schedule not found."}, status=status.HTTP_404_NOT_FOUND
        )

    sched.enabled = not sched.enabled
    sched.save(update_fields=["enabled", "updated_at"])

    try:
        sched_module.register_schedule(sched)
    except Exception:
        pass

    sched.refresh_from_db()
    return Response(_serialize_schedule(sched))


@api_view(["DELETE"])
@permission_classes([IsAdminUser])  # destructive: removes a schedule + its job
def delete_schedule(request, schedule_id):
    """Delete a schedule and remove the APScheduler job."""
    from .. import scheduler as sched_module

    try:
        sched = BackupSchedule.objects.get(id=schedule_id)
    except BackupSchedule.DoesNotExist:
        return Response(
            {"error": "Schedule not found."}, status=status.HTTP_404_NOT_FOUND
        )

    sched_module.deregister_schedule(sched.db_name)
    sched.delete()
    return Response({"message": "Schedule deleted."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def preview_next_runs(request):
    """
    Given schedule params, return the next 5 scheduled run times (preview only, nothing saved).
    """
    import datetime

    frequency = request.data.get("frequency", "daily")
    hour = int(request.data.get("hour", 2))
    minute = int(request.data.get("minute", 0))
    day_of_week = request.data.get("day_of_week")
    day_of_month = request.data.get("day_of_month")
    cron_expression = request.data.get("cron_expression", "")

    # Build a temporary BackupSchedule-like object
    class _FakeSched:
        pass

    fake = _FakeSched()
    fake.frequency = frequency
    fake.hour = hour
    fake.minute = minute
    fake.day_of_week = int(day_of_week) if day_of_week is not None else None
    fake.day_of_month = int(day_of_month) if day_of_month is not None else None
    fake.cron_expression = cron_expression

    from .. import scheduler as sched_module

    try:
        trigger = sched_module._build_trigger(fake)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    runs = []
    prev = now
    for _ in range(5):
        next_fire = trigger.get_next_fire_time(prev, prev)
        if next_fire is None:
            break
        runs.append(next_fire.isoformat())
        prev = next_fire + datetime.timedelta(seconds=1)

    return Response({"next_runs": runs})


def _serialize_schedule(s):
    return {
        "id": str(s.id),
        "db_name": s.db_name,
        "enabled": s.enabled,
        "frequency": s.frequency,
        "hour": s.hour,
        "minute": s.minute,
        "day_of_week": s.day_of_week,
        "day_of_month": s.day_of_month,
        "cron_expression": s.cron_expression,
        "retain_last_n": s.retain_last_n,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def db_info(request):
    """
    Return metadata about every database this tool manages — the main ERP database
    and the system database — so the UI can list both as backup targets. The
    ``restorable`` flag lets the UI hide/disable restore for backup-only databases.
    """
    _sync_orphaned_backups()

    databases = []
    for alias in BACKUP_DB_ALIASES:
        cfg = _get_db_config(alias)

        db_size = None
        try:
            # pg_database_size() is a catalog function, so the size of any database can
            # be read from the default connection by name.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(%s)", [cfg["name"]])
                row = cursor.fetchone()
                db_size = row[0] if row else None
        except Exception:
            pass

        backup_count = BackupRecord.objects.filter(db_name=cfg["name"]).count()
        last_backup = BackupRecord.objects.filter(
            db_name=cfg["name"], status="success"
        ).first()

        databases.append(
            {
                "id": cfg["name"],
                "name": f"{cfg['name']} (PostgreSQL)",
                "engine": "postgresql",
                "host": cfg["host"],
                "port": cfg["port"],
                "size_bytes": db_size,
                "backup_count": backup_count,
                "last_backup_at": last_backup.created_at.isoformat()
                if last_backup
                else None,
                "status": "online",
                "restorable": _is_restorable(cfg["name"]),
            }
        )

    return Response(databases)
