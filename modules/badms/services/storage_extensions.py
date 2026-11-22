from django.conf import settings
from django.db import transaction
from django.db.models import Sum

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.badms.models import ArchiveRequest, AuditEvent, StorageExtensionRequest
from modules.badms.services import notifications


@transaction.atomic
def submit(*, actor, department: str, requester_email: str, requested_bytes: int,
           justification: str, attachment_key: str = "") -> StorageExtensionRequest:
    quota = getattr(settings, "BADMS_USER_QUOTA_BYTES", None)
    available = getattr(settings, "BADMS_AVAILABLE_STORAGE_BYTES", None)
    if not isinstance(quota, int) or quota < 1 or not isinstance(available, int):
        raise ConflictError("Institute storage quota and capacity are not configured.",
                            code="storage_policy_missing")
    usage = ArchiveRequest.objects.filter(user_id=actor.user_id).aggregate(
        total=Sum("attachment_size_bytes"))["total"] or 0
    if usage < quota:
        raise ConflictError("A storage extension is available only when the quota is full.",
                            code="quota_not_full")
    if requested_bytes > available:
        raise BadRequestError("Requested storage exceeds available infrastructure.",
                              code="infrastructure_capacity_exceeded")
    row = StorageExtensionRequest.objects.create(
        user_id=actor.user_id, department=department, requester_email=requester_email,
        requested_bytes=requested_bytes, justification=justification,
        attachment_key=attachment_key, usage_bytes=usage, available_bytes=available)
    AuditEvent.objects.create(actor_user_id=actor.user_id, department=department,
                              action="storage_extension.submit",
                              object_type="storage_extension_request",
                              object_id=str(row.pk), outcome="Submitted")
    hod_emails = getattr(settings, "BADMS_HOD_EMAILS", {}).get(department, [])
    if isinstance(hod_emails, str):
        hod_emails = [hod_emails]
    notifications.enqueue([requester_email, *hod_emails],
                          subject="Storage-extension request submitted",
                          body=f"Storage request {row.pk} was submitted.")
    return row


@transaction.atomic
def decide(*, request_id: int, actor, department: str, approve: bool,
           note: str) -> StorageExtensionRequest:
    row = StorageExtensionRequest.objects.select_for_update().filter(
        pk=request_id, department=department, status="Submitted").exclude(
            user_id=actor.user_id).first()
    if row is None:
        raise NotFoundError("No pending storage-extension request in your department.")
    row.status = "Approved" if approve else "Rejected"
    row.decision_by = actor.user_id
    row.decision_note = note
    row.save(update_fields=["status", "decision_by", "decision_note", "updated_at"])
    AuditEvent.objects.create(actor_user_id=actor.user_id, department=department,
                              action="storage_extension.decision",
                              object_type="storage_extension_request",
                              object_id=str(row.pk), outcome=row.status,
                              details={"note": note})
    notifications.enqueue([row.requester_email], subject="Storage-extension decision",
                          body=f"Your storage-extension request {row.pk} is {row.status}.")
    return row
