import hashlib

from django.conf import settings
from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.badms.domain.transitions import ARCHIVE_TRANSITIONS, next_state
from modules.badms.models import ArchiveRequest, AuditEvent
from modules.badms.services import notifications
from modules.badms.services.storage import retention_deadline


@transaction.atomic
def decide(*, request_id: int, actor, department: str, approve: bool,
           note: str = "") -> ArchiveRequest:
    row = ArchiveRequest.objects.select_for_update().filter(
        pk=request_id, department=department, status="Submitted").exclude(
            user_id=actor.user_id).first()
    if row is None:
        raise NotFoundError("No pending archival request in your department.")
    action = "hod_approve" if approve else "hod_reject"
    row.status = next_state(ARCHIVE_TRANSITIONS, row.status, action)
    row.decision_by = actor.user_id
    row.decision_note = note
    row.save(update_fields=["status", "decision_by", "decision_note", "updated_at"])
    AuditEvent.objects.create(
        actor_user_id=actor.user_id, department=department,
        action="archive.hod_decision", object_type="archive_request",
        object_id=str(row.pk), outcome=row.status, details={"note": note})
    notifications.enqueue([row.requester_email], subject="Archival request decision",
                          body=f"Your archival request {row.pk} is {row.status}.")
    return row


@transaction.atomic
def classify(*, request_id: int, actor, classification: str) -> ArchiveRequest:
    row = ArchiveRequest.objects.select_for_update().filter(
        pk=request_id, status="HoD Approved").exclude(user_id=actor.user_id).first()
    if row is None:
        raise NotFoundError("No approved archival request is available for classification.")
    if classification not in dict(ArchiveRequest.CLASSIFICATION):
        raise ConflictError("Unsupported classification.", code="invalid_classification")
    retention_until = retention_deadline(classification)
    action = "classify_sensitive" if classification == "Sensitive" else "classify_other"
    row.status = next_state(ARCHIVE_TRANSITIONS, row.status, action)
    row.classification = classification
    row.classified_by = actor.user_id
    row.retention_until = retention_until
    if classification != "Sensitive":
        row.archive_key = row.attachment_key
    row.save(update_fields=["status", "classification", "classified_by",
                            "retention_until", "archive_key", "updated_at"])
    AuditEvent.objects.create(
        actor_user_id=actor.user_id, department=row.department,
        action="archive.classify", object_type="archive_request",
        object_id=str(row.pk), outcome=row.status,
        details={"classification": classification})
    if classification == "Sensitive":
        notifications.enqueue(settings.BADMS_IT_SECURITY_EMAILS,
                              subject="Sensitive archive requires security handling",
                              body=f"Archival request {row.pk} awaits IT Security.")
    return row


@transaction.atomic
def create_sensitive_archive(*, request_id: int, actor) -> ArchiveRequest:

    from modules.badms.services.storage import badms_storage, require_secure_storage

    row = ArchiveRequest.objects.select_for_update().filter(
        pk=request_id,
        status="Classified Sensitive / Routed to IT Security",
        classification="Sensitive").exclude(user_id=actor.user_id).first()
    if row is None:
        raise NotFoundError("No Sensitive archive is awaiting IT Security.")
    require_secure_storage()
    storage = badms_storage()
    if not storage.exists(row.attachment_key):
        raise ConflictError("The source archive object is unavailable.",
                            code="archive_source_unavailable")
    key = f"badms/archives/{row.pk}/content"
    with storage.open(row.attachment_key, "rb") as source:
        saved_key = storage.save(key, source)
    digest = hashlib.sha256()
    with storage.open(saved_key, "rb") as saved:
        for chunk in iter(lambda: saved.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != row.checksum_sha256:
        storage.delete(saved_key)
        raise ConflictError("Sensitive archive integrity verification failed.",
                            code="archive_integrity_failed")
    row.archive_key = saved_key
    row.status = next_state(ARCHIVE_TRANSITIONS, row.status, "encrypt")
    row.save(update_fields=["archive_key", "status", "updated_at"])
    AuditEvent.objects.create(
        actor_user_id=actor.user_id, department=row.department,
        action="archive.sensitive_created", object_type="archive_request",
        object_id=str(row.pk), outcome=row.status,
        details={"storage_encryption": "AES-256", "transport": "TLS"})
    notifications.enqueue([row.requester_email], subject="Sensitive archive created",
                          body=f"Your archival request {row.pk} has been archived.")
    return row
