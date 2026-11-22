from django.conf import settings
from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.badms.domain.transitions import RESTORE_TRANSITIONS, next_state
from modules.badms.models import ArchiveRequest, AuditEvent, RestorationRequest
from modules.badms.services import notifications
from modules.badms.services.storage import badms_storage, require_secure_storage


@transaction.atomic
def request_restore(*, actor, archive_id: int) -> RestorationRequest:
    archive = ArchiveRequest.objects.filter(pk=archive_id, user_id=actor.user_id).first()
    if archive is None or not archive.archive_key:
        raise NotFoundError("No restorable archive was found.")
    state = ("Sensitive Restoration Pending Approval"
             if archive.classification == "Sensitive"
             else "Restoration Requested / Standard Path")
    row = RestorationRequest.objects.create(
        user_id=actor.user_id, department=archive.department,
        requester_email=getattr(actor, "email", ""), archive_request=archive,
        classification=archive.classification, status=state)
    AuditEvent.objects.create(actor_user_id=actor.user_id, department=archive.department,
                              action="restore.request", object_type="restoration_request",
                              object_id=str(row.pk), outcome=state)
    if state == "Sensitive Restoration Pending Approval":
        notifications.enqueue(settings.BADMS_SYSADMIN_EMAILS,
                              subject="Sensitive restoration requires approval",
                              body=f"Restoration request {row.pk} awaits SysAdmin approval.")
    return row


@transaction.atomic
def decide_sensitive(*, request_id: int, actor, approve: bool) -> RestorationRequest:
    row = RestorationRequest.objects.select_for_update().filter(
        pk=request_id, status="Sensitive Restoration Pending Approval").exclude(
            user_id=actor.user_id).first()
    if row is None:
        raise NotFoundError("No pending Sensitive restoration request was found.")
    row.status = next_state(RESTORE_TRANSITIONS, row.status,
                            "approve" if approve else "reject")
    row.decision_by = actor.user_id
    row.save(update_fields=["status", "decision_by", "updated_at"])
    AuditEvent.objects.create(actor_user_id=actor.user_id, department=row.department,
                              action="restore.sensitive_decision",
                              object_type="restoration_request", object_id=str(row.pk),
                              outcome=row.status)
    notifications.enqueue([row.requester_email], subject="Restoration decision",
                          body=f"Your restoration request {row.pk} is {row.status}.")
    return row


@transaction.atomic
def execute_restore(*, request_id: int, actor) -> RestorationRequest:
    row = RestorationRequest.objects.select_for_update().select_related(
        "archive_request").filter(pk=request_id).exclude(user_id=actor.user_id).first()
    if row is None:
        raise NotFoundError("No restoration request was found.")
    if row.status not in ("Restoration Requested / Standard Path",
                          "Approved for Restoration"):
        raise ConflictError("This restoration is not approved for execution.",
                            code="restore_not_approved")
    if row.classification == "Sensitive":
        require_secure_storage()
    source = row.archive_request.archive_key
    storage = badms_storage()
    if not source or not storage.exists(source):
        raise ConflictError("The archive object is unavailable.", code="archive_unavailable")
    key = f"badms/restored/{row.user_id}/{row.pk}/archive"
    with storage.open(source, "rb") as stream:
        key = storage.save(key, stream)
    row.status = next_state(RESTORE_TRANSITIONS, row.status, "restore")
    row.restored_key = key
    row.outcome = "Archive restored to private recovery storage."
    row.save(update_fields=["status", "restored_key", "outcome", "updated_at"])
    AuditEvent.objects.create(actor_user_id=actor.user_id, department=row.department,
                              action="restore.execute", object_type="restoration_request",
                              object_id=str(row.pk), outcome=row.status)
    notifications.enqueue([row.requester_email], subject="Restoration completed",
                          body=f"Your restoration request {row.pk} has been completed.")
    return row
