import logging

from django.conf import settings
from django.db import DatabaseError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.badms.domain.departments import department_code
from modules.badms.domain.state_machine import InvalidTransition, transition
from modules.badms.models import (
    ArchivalRequest,
    RestoreRequest,
    StorageExtensionRequest,
    StorageObservation,
)
from modules.badms.selectors.scoping import (
    archival_requests_for,
    restoration_requests_for,
    storage_extensions_for,
)
from modules.badms.services import audit, notifications, storage
from modules.badms.services.authz import require, require_department_role
from modules.directory import contracts as directory

log = logging.getLogger("fusion.badms.workflows")

def _actor_id(actor) -> int:
    actor_id = getattr(actor, "user_id", None)
    if actor_id is None:
        raise NotFoundError("The authenticated user has no directory identity.")
    return int(actor_id)


def _department_for(actor_id: int) -> str:
    people = directory.get_users([actor_id])
    person = people.get(actor_id)
    if person is None:
        raise NotFoundError("The requester was not found in the directory.")
    values = (person.discipline, person.department)
    department = next(
        (department_code(value) for value in values if value.strip()),
        "",
    )
    if not department:
        raise ConflictError(
            "A department is not available for this account.",
            code="department_unavailable",
        )
    return department


def _capacity_for(user_id: int) -> StorageObservation:
    try:
        used = storage.user_usage_bytes(user_id)
    except storage.StorageError as exc:
        raise ConflictError(
            "Storage capacity could not be measured.",
            code=exc.code,
        ) from exc
    return StorageObservation.objects.create(
        user_id=user_id,
        used_bytes=used,
        quota_bytes=settings.BADMS_USER_QUOTA_BYTES,
    )


def _store_attachment(*, upload, user_id: int) -> storage.StoredObject:
    key = storage.new_object_key(user_id=user_id, category="archives")
    source = getattr(upload, "file", upload)
    if hasattr(source, "seek"):
        source.seek(0)
    return storage.store_stream(
        source,
        key=key,
        owner=f"archive-requester:{user_id}",
    )


def _queue_archival(row_id: int) -> None:
    from modules.badms.tasks import finalize_archival

    transaction.on_commit(lambda: finalize_archival.delay(row_id))


def submit_archival_request(*, actor, data: dict) -> ArchivalRequest:
    actor_id = _actor_id(actor)
    observation = _capacity_for(actor_id)
    attachment = data["attachment"]
    if observation.used_bytes + attachment.size > observation.quota_bytes:
        raise ConflictError("The storage quota is full.",
                            code="storage_quota_full")
    department = _department_for(actor_id)
    stored = _store_attachment(upload=attachment, user_id=actor_id)
    try:
        with transaction.atomic():
            row = ArchivalRequest.objects.create(
                requester_user_id=actor_id,
                department_code=department,
                file_name=data["file_name"],
                data_date=data["data_date"],
                owners=data["owners"],
                file_type=data["file_type"],
                reason=data["reason"],
                attachment_key=stored.key,
                attachment_sha256=stored.sha256,
                attachment_size_bytes=stored.size_bytes,
                initial_classification=data.get(
                    "initial_classification",
                    ArchivalRequest.Classification.ROUTINE,
                ),
            )
            audit.record(
                actor_user_id=actor_id,
                action="submit",
                resource="archive",
                resource_id=str(row.pk),
            )
            notifications.enqueue_user(
                user_id=actor_id,
                subject="Archival request submitted",
                body=f"Your BADMS archival request {row.pk} was submitted.",
                resource="archive",
                resource_id=str(row.pk),
            )
    except DatabaseError:
        try:
            storage.delete_object(stored.key)
        except storage.StorageError:
            log.exception("badms.archive.orphan_cleanup_failed user_id=%s", actor_id)
        raise
    return row


def submit_special_archival(*, actor, data: dict) -> ArchivalRequest:
    require(actor, "badms.archive.create")
    if getattr(actor, "active_role", None) != "Super Admin":
        raise ConflictError("Only Super Admin may perform special archival.",
                            code="permission_denied")
    actor_id = _actor_id(actor)
    attachment = data["attachment"]
    stored = _store_attachment(upload=attachment, user_id=actor_id)
    try:
        with transaction.atomic():
            row = ArchivalRequest.objects.create(
                requester_user_id=actor_id,
                department_code="",
                file_name=data["file_name"],
                data_date=data["data_date"],
                owners=data["owners"],
                file_type=data["file_type"],
                reason=data["reason"],
                attachment_key=stored.key,
                attachment_sha256=stored.sha256,
                attachment_size_bytes=stored.size_bytes,
                initial_classification=ArchivalRequest.Classification.ARCHIVAL,
                classification=ArchivalRequest.Classification.ARCHIVAL,
                status=transition(
                    "archive", ArchivalRequest.Status.SUBMITTED,
                    "special_archive", "super_admin",
                ),
                decision_by_user_id=actor_id,
                decision_at=timezone.now(),
                special_operation=True,
            )
            audit.record(
                actor_user_id=actor_id,
                action="special_archive_submitted",
                resource="archive",
                resource_id=str(row.pk),
                details={"special_operation": True},
            )
            _queue_archival(row.pk)
    except DatabaseError:
        try:
            storage.delete_object(stored.key)
        except storage.StorageError:
            log.exception("badms.special_archive.orphan_cleanup_failed user_id=%s",
                          actor_id)
        raise
    return row


def finalize_archival_request(request_id: int) -> str:
    row = ArchivalRequest.objects.filter(pk=request_id).first()
    if row is None:
        raise NotFoundError("Archival request not found.")
    if row.status not in {
        ArchivalRequest.Status.CLASSIFIED,
        ArchivalRequest.Status.READY_TO_ARCHIVE,
    }:
        return row.status
    if not row.attachment_key:
        error_code = "archive_attachment_missing"
    else:
        try:
            storage.verify_object(
                key=row.attachment_key,
                expected_sha256=row.attachment_sha256,
                expected_size=row.attachment_size_bytes,
            )
        except storage.StorageError as exc:
            error_code = exc.code
        else:
            error_code = ""

    with transaction.atomic():
        row = ArchivalRequest.objects.select_for_update().get(pk=request_id)
        if row.status not in {
            ArchivalRequest.Status.CLASSIFIED,
            ArchivalRequest.Status.READY_TO_ARCHIVE,
        }:
            return row.status
        if error_code:
            row.status = transition(
                "archive", row.status, "archive_failed", "system",
            )
            row.decision_reason = error_code
            row.save(update_fields=["status", "decision_reason", "updated_at"])
            audit.record(
                actor_user_id=None,
                action="archive_failed",
                resource="archive",
                resource_id=str(row.pk),
                outcome="failure",
                details={"error_code": error_code},
            )
            notifications.enqueue_emails(
                recipients=settings.BADMS_SYSADMIN_EMAILS,
                subject="BADMS archival failed",
                body=f"Archival request {row.pk} failed with {error_code}.",
                resource="archive",
                resource_id=str(row.pk),
            )
        else:
            row.status = transition(
                "archive", row.status, "archive_succeeded", "system",
            )
            row.storage_key = row.attachment_key
            row.save(update_fields=["status", "storage_key", "updated_at"])
            audit.record(
                actor_user_id=None,
                action="archive_succeeded",
                resource="archive",
                resource_id=str(row.pk),
                details={"classification": row.classification},
            )
            notifications.enqueue_user(
                user_id=row.requester_user_id,
                subject="Archival request completed",
                body=f"Your BADMS archival request {row.pk} is archived.",
                resource="archive",
                resource_id=str(row.pk),
            )
    return row.status


@transaction.atomic
def decide_archival_request(*, actor, request_id: int, approved: bool,
                            reason: str = "") -> ArchivalRequest:
    require(actor, "badms.archive.approve")
    require(actor, "badms.archive.review")
    row = archival_requests_for(actor).select_for_update().filter(
        pk=request_id,
    ).first()
    if row is None:
        raise NotFoundError("Archival request not found.")
    require_department_role(actor, row.department_code)
    event = "approve" if approved else "reject"
    try:
        row.status = transition("archive", row.status, event, "hod")
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    row.decision_by_user_id = _actor_id(actor)
    row.decision_at = timezone.now()
    row.decision_reason = reason
    row.save(update_fields=["status", "decision_by_user_id", "decision_at",
                            "decision_reason", "updated_at"])
    audit.record(actor_user_id=row.decision_by_user_id, action=event,
                 resource="archive", resource_id=str(row.pk),
                 details={"department_code": row.department_code})
    notifications.enqueue_user(
        user_id=row.requester_user_id,
        subject=f"Archival request {row.status}",
        body=f"Your BADMS archival request {row.pk} was {row.status}.",
        resource="archive",
        resource_id=str(row.pk),
    )
    if approved:
        notifications.enqueue_emails(
            recipients=settings.BADMS_SYSADMIN_EMAILS,
            subject="Archival request requires classification",
            body=f"Archival request {row.pk} is awaiting SysAdmin classification.",
            resource="archive",
            resource_id=str(row.pk),
        )
    return row


@transaction.atomic
def classify_archival_request(*, actor, request_id: int,
                              classification: str) -> ArchivalRequest:
    require(actor, "badms.archive.assign")
    row = archival_requests_for(actor).select_for_update().filter(
        pk=request_id,
    ).first()
    if row is None:
        raise NotFoundError("Archival request not found.")
    if classification not in ArchivalRequest.Classification.values:
        raise ConflictError("Unknown data classification.",
                            code="invalid_classification")
    event = ("classify_sensitive"
             if classification == ArchivalRequest.Classification.SENSITIVE
             else "classify_non_sensitive")
    try:
        row.status = transition("archive", row.status, event, "sysadmin")
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    row.classification = classification
    row.decision_by_user_id = _actor_id(actor)
    row.decision_at = timezone.now()
    row.save(update_fields=["status", "classification", "decision_by_user_id",
                            "decision_at", "updated_at"])
    audit.record(actor_user_id=row.decision_by_user_id, action="classify",
                 resource="archive", resource_id=str(row.pk),
                 details={"classification": classification})
    if classification == ArchivalRequest.Classification.SENSITIVE:
        notifications.enqueue_emails(
            recipients=settings.BADMS_IT_SECURITY_EMAILS,
            subject="Sensitive archival requires security review",
            body=f"Archival request {row.pk} requires BADMS security review.",
            resource="archive",
            resource_id=str(row.pk),
        )
    if row.status == ArchivalRequest.Status.CLASSIFIED:
        _queue_archival(row.pk)
    return row


@transaction.atomic
def mark_encryption_configured(*, actor, request_id: int) -> ArchivalRequest:
    require(actor, "badms.encryption.manage")
    row = archival_requests_for(actor).select_for_update().filter(
        pk=request_id, classification=ArchivalRequest.Classification.SENSITIVE,
    ).first()
    if row is None:
        raise NotFoundError("Sensitive archival request not found.")
    try:
        row.status = transition(
            "archive", row.status, "encryption_configured", "it_security",
        )
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    row.decision_by_user_id = _actor_id(actor)
    row.decision_at = timezone.now()
    row.save(update_fields=["status", "decision_by_user_id", "decision_at",
                            "updated_at"])
    audit.record(actor_user_id=row.decision_by_user_id,
                 action="encryption_configured", resource="archive",
                 resource_id=str(row.pk))
    _queue_archival(row.pk)
    return row


@transaction.atomic
def submit_restore_request(*, actor, archive_id: int, reason: str) -> RestoreRequest:
    actor_id = _actor_id(actor)
    archive = archival_requests_for(actor).filter(
        pk=archive_id, status=ArchivalRequest.Status.ARCHIVED,
    ).first()
    if archive is None:
        raise NotFoundError("Archived data not found.")
    if archive.requester_user_id != actor_id:
        raise NotFoundError("Archived data not found.")
    row = RestoreRequest.objects.create(
        archive=archive, requester_user_id=actor_id, reason=reason,
    )
    audit.record(actor_user_id=actor_id, action="submit", resource="restore",
                 resource_id=str(row.pk))
    if archive.classification == ArchivalRequest.Classification.SENSITIVE:
        notifications.enqueue_emails(
            recipients=settings.BADMS_SYSADMIN_EMAILS,
            subject="Sensitive restoration requires approval",
            body=f"Restoration request {row.pk} requires SysAdmin approval.",
            resource="restore",
            resource_id=str(row.pk),
        )
    return row


@transaction.atomic
def decide_restore_request(*, actor, request_id: int,
                           approved: bool) -> RestoreRequest:
    require(actor, "badms.restore.approve")
    row = restoration_requests_for(actor).select_for_update().filter(
        pk=request_id,
        archive__classification=ArchivalRequest.Classification.SENSITIVE,
    ).first()
    if row is None:
        raise NotFoundError("Sensitive restoration request not found.")
    event = "approve" if approved else "reject"
    try:
        row.status = transition(
            "restore", "submitted_sensitive", event, "sysadmin",
        )
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    row.decision_by_user_id = _actor_id(actor)
    row.decision_at = timezone.now()
    row.save(update_fields=["status", "decision_by_user_id", "decision_at",
                            "updated_at"])
    audit.record(actor_user_id=row.decision_by_user_id, action=event,
                 resource="restore", resource_id=str(row.pk))
    notifications.enqueue_user(
        user_id=row.requester_user_id,
        subject=f"Restoration request {row.status}",
        body=f"Your BADMS restoration request {row.pk} is {row.status}.",
        resource="restore",
        resource_id=str(row.pk),
    )
    return row


def execute_restore_request(*, actor, request_id: int) -> tuple[RestoreRequest, str]:
    require(actor, "badms.restore.restore")
    row = restoration_requests_for(actor).select_related("archive").filter(
        pk=request_id,
    ).first()
    if row is None:
        raise NotFoundError("Restoration request not found.")
    if (row.requester_user_id != _actor_id(actor)
            and getattr(actor, "active_role", None) not in {
                "SysAdmin", "Super Admin",
            }):
        raise NotFoundError("Restoration request not found.")

    sensitive = row.archive.classification == ArchivalRequest.Classification.SENSITIVE
    if sensitive and row.status not in {
        RestoreRequest.Status.APPROVED,
        RestoreRequest.Status.RESTORING,
        RestoreRequest.Status.RESTORED,
    }:
        raise ConflictError(
            "Sensitive restoration requires SysAdmin approval.",
            code="restore_not_approved",
        )
    if not sensitive and row.status not in {
        RestoreRequest.Status.SUBMITTED,
        RestoreRequest.Status.RESTORING,
        RestoreRequest.Status.RESTORED,
    }:
        raise ConflictError("This restoration request is not executable.",
                            code="invalid_restore_state")
    if not row.archive.storage_key:
        raise ConflictError("The archived artifact is unavailable.",
                            code="archive_unavailable")

    if row.status not in {
        RestoreRequest.Status.RESTORING,
        RestoreRequest.Status.RESTORED,
    }:
        source_state = (
            "approved" if sensitive else "submitted_standard"
        )
        try:
            target = transition(
                "restore", source_state, "execute", "system",
            )
        except InvalidTransition as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc
        row.status = target
        row.save(update_fields=["status", "updated_at"])

    try:
        path = storage.decrypt_object_to_temp(
            key=row.archive.storage_key,
            owner=f"archive-requester:{row.archive.requester_user_id}",
        )
    except storage.StorageError as exc:
        row.status = transition("restore", row.status, "failed", "system")
        row.error_code = exc.code
        row.save(update_fields=["status", "error_code", "updated_at"])
        audit.record(
            actor_user_id=_actor_id(actor),
            action="restore_failed",
            resource="restore",
            resource_id=str(row.pk),
            outcome="failure",
            details={"error_code": exc.code},
        )
        notifications.enqueue_user(
            user_id=row.requester_user_id,
            subject="Restoration failed",
            body=f"Your BADMS restoration request {row.pk} failed.",
            resource="restore",
            resource_id=str(row.pk),
        )
        raise ConflictError(
            "The archived artifact could not be restored.",
            code=exc.code,
        ) from exc

    if row.status != RestoreRequest.Status.RESTORED:
        row.status = transition("restore", row.status, "succeeded", "system")
    row.error_code = ""
    row.save(update_fields=["status", "error_code", "updated_at"])
    audit.record(
        actor_user_id=_actor_id(actor),
        action="restore_succeeded",
        resource="restore",
        resource_id=str(row.pk),
    )
    notifications.enqueue_user(
        user_id=row.requester_user_id,
        subject="Restoration completed",
        body=f"Your BADMS restoration request {row.pk} is ready.",
        resource="restore",
        resource_id=str(row.pk),
    )
    return row, path


def submit_storage_extension(*, actor, requested_bytes: int,
                             justification: str) -> StorageExtensionRequest:
    actor_id = _actor_id(actor)
    observation = _capacity_for(actor_id)
    if observation.used_bytes < observation.quota_bytes:
        raise ConflictError("A storage extension is available only at full quota.",
                            code="quota_not_full")
    available = settings.BADMS_AVAILABLE_CAPACITY_BYTES
    if available is None:
        raise ConflictError(
            "Infrastructure capacity is not currently available.",
            code="infrastructure_capacity_unavailable",
        )
    if requested_bytes > available:
        raise ConflictError(
            "The requested capacity exceeds available infrastructure capacity.",
            code="insufficient_infrastructure_capacity",
        )
    department = _department_for(actor_id)
    with transaction.atomic():
        row = StorageExtensionRequest.objects.create(
            requester_user_id=actor_id,
            department_code=department,
            current_usage_bytes=observation.used_bytes,
            quota_bytes=observation.quota_bytes,
            requested_bytes=requested_bytes,
            justification=justification,
        )
        audit.record(actor_user_id=actor_id, action="submit",
                     resource="storage_extension", resource_id=str(row.pk))
        notifications.enqueue_user(
            user_id=actor_id,
            subject="Storage extension request submitted",
            body=f"Your BADMS storage extension request {row.pk} was submitted.",
            resource="storage_extension",
            resource_id=str(row.pk),
        )
    return row


@transaction.atomic
def decide_storage_extension(*, actor, request_id: int, approved: bool,
                             reason: str = "") -> StorageExtensionRequest:
    require(actor, "badms.storage_extension.approve")
    require(actor, "badms.storage_extension.review")
    row = storage_extensions_for(actor).select_for_update().filter(
        pk=request_id,
    ).first()
    if row is None:
        raise NotFoundError("Storage-extension request not found.")
    require_department_role(actor, row.department_code)
    event = "approve" if approved else "reject"
    try:
        row.status = transition("storage_extension", row.status, event, "hod")
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    row.decision_by_user_id = _actor_id(actor)
    row.decision_at = timezone.now()
    row.decision_reason = reason
    row.save(update_fields=["status", "decision_by_user_id", "decision_at",
                            "decision_reason", "updated_at"])
    audit.record(actor_user_id=row.decision_by_user_id, action=event,
                 resource="storage_extension", resource_id=str(row.pk),
                 details={"department_code": row.department_code})
    notifications.enqueue_user(
        user_id=row.requester_user_id,
        subject=f"Storage extension {row.status}",
        body=f"Your BADMS storage extension request {row.pk} is {row.status}.",
        resource="storage_extension",
        resource_id=str(row.pk),
    )
    return row
