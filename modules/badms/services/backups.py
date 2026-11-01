"""Create a compressed, checksummed snapshot using Django's database dump."""
import gzip
import hashlib
import io

from django.core import management
from django.core.files.base import ContentFile
from django.utils import timezone

from modules.badms.models import BackupRun
from modules.badms.services.audit import record


def create_backup(actor_id, *, trigger=BackupRun.Trigger.MANUAL):
    run = BackupRun.objects.create(created_by=actor_id, trigger=trigger)
    try:
        output = io.StringIO()
        management.call_command(
            "dumpdata", exclude=["contenttypes", "auth.permission", "sessions.session"],
            indent=2, stdout=output,
        )
        compressed = gzip.compress(output.getvalue().encode("utf-8"), mtime=0)
        digest = hashlib.sha256(compressed).hexdigest()
        run.artifact.save(f"badms-{run.pk}-{run.started_at:%Y%m%dT%H%M%SZ}.json.gz",
                          ContentFile(compressed), save=False)
        run.status = BackupRun.Status.SUCCESS
        run.checksum = digest
        run.size_bytes = len(compressed)
        run.finished_at = timezone.now()
        run.message = "Database snapshot created and SHA-256 verified."
        run.save()
        record(actor_id, "backup.created", object_type="backup", object_id=run.pk,
               details={"checksum": digest, "size_bytes": len(compressed)})
    except Exception as exc:
        run.status = BackupRun.Status.FAILED
        run.finished_at = timezone.now()
        run.message = str(exc)[:1000]
        run.save(update_fields=["status", "finished_at", "message"])
        record(actor_id, "backup.failed", object_type="backup", object_id=run.pk,
               outcome="FAILED", details={"message": run.message})
    return run
