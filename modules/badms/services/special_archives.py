import hashlib

from django.db import transaction

from core.files.validators import sanitise_filename
from modules.badms.models import AuditEvent, SpecialArchiveOperation
from modules.badms.services.storage import badms_storage, require_secure_storage


@transaction.atomic
def perform(*, actor, offline_request_reference: str, research_description: str,
            upload) -> SpecialArchiveOperation:
    require_secure_storage()
    safe = sanitise_filename(upload.name, fallback="research-archive")
    storage = badms_storage()
    key = storage.save(f"badms/special/{actor.user_id}/{safe}", upload)
    digest = hashlib.sha256()
    try:
        with storage.open(key, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        row = SpecialArchiveOperation.objects.create(
            actor_user_id=actor.user_id,
            offline_request_reference=offline_request_reference,
            research_description=research_description,
            archive_key=key, checksum_sha256=digest.hexdigest())
    except Exception:
        storage.delete(key)
        raise
    AuditEvent.objects.create(actor_user_id=actor.user_id,
                              action="archive.special.perform",
                              object_type="special_archive_operation",
                              object_id=str(row.pk), outcome=row.outcome,
                              details={"checksum_sha256": row.checksum_sha256})
    return row
