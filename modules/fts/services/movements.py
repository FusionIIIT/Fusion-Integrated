"""File forwarding and return services for FTS."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.fts.domain.entities import (
    validate_employee_operational_actor,
    validate_mandatory_comment,
    validate_recipient,
)
from modules.fts.domain.errors import (
    ArchivedFileModificationProhibitedError,
    FtsDomainError,
    InvalidRecipientError,
    MandatoryCommentMissingError,
    SystemAdminOperationalActionProhibitedError,
)
from modules.fts.domain.state_machine import (
    ACTION_FORWARD,
    ACTION_RETURN,
    ACTION_SEND_INITIAL,
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
    transition_state,
)
from modules.fts.models.attachments import FileAttachment
from modules.fts.models.comments import FileComment
from modules.fts.models.files import File
from modules.fts.models.movements import FileMovement
from modules.fts.services.audit import record_audit
from modules.fts.services.notifications import trigger_notification


def _validate_forward_inputs(
    actor_kind: str,
    is_admin_actor: bool,
    comment_text: str,
    to_user_id: int,
) -> tuple[str, int]:
    """Validates parameters and actor credentials for forwarding a file."""
    try:
        validate_employee_operational_actor(actor_kind, is_admin_actor)
        valid_comment = validate_mandatory_comment(comment_text)
        valid_to_id = validate_recipient(to_user_id)
    except MandatoryCommentMissingError as e:
        raise BadRequestError(str(e), code="mandatory_comment_missing") from e
    except InvalidRecipientError as e:
        raise BadRequestError(str(e), code="invalid_recipient") from e
    except SystemAdminOperationalActionProhibitedError as e:
        raise PermissionDeniedError(str(e), code="admin_operational_action_prohibited") from e
    except FtsDomainError as e:
        raise BadRequestError(str(e), code="fts_validation_error") from e
    else:
        return valid_comment, valid_to_id


def _validate_forward_custody(file_obj: File, actor_user_id: int) -> str:
    """Verifies that the file can be transitioned and actor is current holder."""
    if file_obj.status == STATE_ARCHIVED:
        raise ConflictError(
            "Archived files cannot be forwarded. The file is permanently closed.",
            code="archived_file_immutable",
        )
    if file_obj.status == STATE_DISCARDED:
        raise ConflictError(
            "Discarded files cannot be forwarded. Create a new draft if needed.",
            code="discarded_file_invalid",
        )
    if file_obj.current_holder_user_id != actor_user_id:
        raise PermissionDeniedError(
            "You are not the current holder of this file and cannot forward it. "
            "Wait for the file to be routed to you.",
            code="not_current_holder",
        )
    action = ACTION_SEND_INITIAL if file_obj.status == STATE_DRAFT else ACTION_FORWARD
    try:
        return transition_state(file_obj.status, action)
    except ArchivedFileModificationProhibitedError as e:
        raise ConflictError(str(e), code="archived_file_immutable") from e
    except FtsDomainError as e:
        raise ConflictError(str(e), code="invalid_state_transition") from e


def _persist_forward_movement(
    file_obj: File,
    next_seq: int,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    valid_to_id: int,
    to_username: str,
    to_role: str,
    valid_comment: str,
    attachments: list[dict[str, Any]] | None,
    target_status: str,
) -> FileMovement:
    """Persists movement, comment, attachments, and updates holder within transaction."""
    movement = FileMovement.objects.create(
        file=file_obj, sequence=next_seq, movement_type="FORWARD",
        from_user_id=actor_user_id, from_username=actor_username, from_role=actor_role,
        to_user_id=valid_to_id, to_username=to_username, to_role=to_role,
    )
    FileComment.objects.create(
        file=file_obj, movement=movement, author_user_id=actor_user_id,
        author_username=actor_username, author_role=actor_role, comment_text=valid_comment,
    )
    if attachments:
        for att in attachments:
            FileAttachment.objects.create(
                file=file_obj, movement=movement, uploader_user_id=actor_user_id,
                uploader_username=actor_username, file_name=att.get("file_name", "attachment"),
                file_url=att.get("file_url", ""), file_size=att.get("file_size", 0),
                mime_type=att.get("mime_type", ""),
            )
    file_obj.status = target_status
    file_obj.current_holder_user_id = valid_to_id
    file_obj.current_holder_username = to_username
    file_obj.current_holder_role = to_role
    file_obj.save(update_fields=[
        "status", "current_holder_user_id", "current_holder_username",
        "current_holder_role", "updated_at",
    ])
    record_audit(
        file_id=file_obj.id, action="FILE_FORWARDED", actor_user_id=actor_user_id,
        actor_username=actor_username, actor_role=actor_role,
        details={"sequence": next_seq, "to_user_id": valid_to_id, "to_username": to_username},
    )
    return movement


def forward_file(
    *,
    file_id: int,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    actor_kind: str = "faculty",
    is_admin_actor: bool = False,
    to_user_id: int,
    to_username: str,
    to_role: str,
    comment_text: str,
    attachments: list[dict[str, Any]] | None = None,
) -> FileMovement:
    """Forwards an actionable file onward or initiates first circulation from draft."""
    valid_comment, valid_to_id = _validate_forward_inputs(
        actor_kind, is_admin_actor, comment_text, to_user_id
    )
    with transaction.atomic():
        try:
            file_obj = File.objects.select_for_update().get(id=file_id)
        except File.DoesNotExist as e:
            raise NotFoundError(f"File #{file_id} was not found.") from e

        target_status = _validate_forward_custody(file_obj, actor_user_id)
        last_seq = (
            FileMovement.objects.filter(file=file_obj)
            .order_by("-sequence")
            .values_list("sequence", flat=True)
            .first() or 0
        )
        movement = _persist_forward_movement(
            file_obj, last_seq + 1, actor_user_id, actor_username, actor_role,
            valid_to_id, to_username, to_role, valid_comment, attachments, target_status,
        )
        trigger_notification(
            event_type="FILE_FORWARDED", recipient_user_id=valid_to_id,
            payload={
                "file_id": file_obj.id, "reference_number": file_obj.reference_number,
                "from": actor_username, "sequence": last_seq + 1,
            },
        )
    return movement


def _validate_return_inputs(
    actor_kind: str,
    is_admin_actor: bool,
    comment_text: str,
) -> str:
    """Validates parameters and actor credentials for returning a file."""
    try:
        validate_employee_operational_actor(actor_kind, is_admin_actor)
        return validate_mandatory_comment(comment_text)
    except MandatoryCommentMissingError as e:
        raise BadRequestError(str(e), code="mandatory_comment_missing") from e
    except SystemAdminOperationalActionProhibitedError as e:
        raise PermissionDeniedError(str(e), code="admin_operational_action_prohibited") from e
    except FtsDomainError as e:
        raise BadRequestError(str(e), code="fts_validation_error") from e


def _validate_return_custody(file_obj: File, actor_user_id: int) -> None:
    """Verifies that the file is circulated and held by the actor."""
    if file_obj.status != STATE_CIRCULATED:
        raise ConflictError(
            "Only active circulated files can be returned. Drafts cannot be returned.",
            code="file_not_circulated",
        )
    if file_obj.current_holder_user_id != actor_user_id:
        raise PermissionDeniedError(
            "You are not the current holder of this file and cannot return it. "
            "Wait for the file to be routed to your inbox.",
            code="not_current_holder",
        )


def _resolve_return_recipient(file_obj: File, actor_user_id: int) -> tuple[int, str, str]:
    """Identifies the prior sender to whom the file is returned."""
    last_movement = FileMovement.objects.filter(file=file_obj).order_by("-sequence").first()
    if not last_movement:
        raise ConflictError(
            "No movement record exists to identify previous sender. Forward the file instead.",
            code="no_previous_sender",
        )
    prev_id = last_movement.from_user_id
    prev_name = last_movement.from_username
    prev_role = last_movement.from_role
    if prev_id == actor_user_id:
        prior = (
            FileMovement.objects.filter(file=file_obj, to_user_id=actor_user_id)
            .order_by("-sequence").first()
        )
        if prior:
            prev_id, prev_name, prev_role = prior.from_user_id, prior.from_username, prior.from_role
    return prev_id, prev_name, prev_role


def _persist_return_movement(
    file_obj: File,
    next_seq: int,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    prev_id: int,
    prev_name: str,
    prev_role: str,
    valid_comment: str,
    attachments: list[dict[str, Any]] | None,
    target_status: str,
) -> FileMovement:
    """Persists return movement record and updates current holder."""
    movement = FileMovement.objects.create(
        file=file_obj, sequence=next_seq, movement_type="RETURN",
        from_user_id=actor_user_id, from_username=actor_username, from_role=actor_role,
        to_user_id=prev_id, to_username=prev_name, to_role=prev_role,
    )
    FileComment.objects.create(
        file=file_obj, movement=movement, author_user_id=actor_user_id,
        author_username=actor_username, author_role=actor_role, comment_text=valid_comment,
    )
    if attachments:
        for att in attachments:
            FileAttachment.objects.create(
                file=file_obj, movement=movement, uploader_user_id=actor_user_id,
                uploader_username=actor_username, file_name=att.get("file_name", "attachment"),
                file_url=att.get("file_url", ""), file_size=att.get("file_size", 0),
                mime_type=att.get("mime_type", ""),
            )
    file_obj.status = target_status
    file_obj.current_holder_user_id = prev_id
    file_obj.current_holder_username = prev_name
    file_obj.current_holder_role = prev_role
    file_obj.save(update_fields=[
        "status", "current_holder_user_id", "current_holder_username",
        "current_holder_role", "updated_at",
    ])
    record_audit(
        file_id=file_obj.id, action="FILE_RETURNED", actor_user_id=actor_user_id,
        actor_username=actor_username, actor_role=actor_role,
        details={"sequence": next_seq, "to_user_id": prev_id, "to_username": prev_name},
    )
    return movement


def return_file(
    *,
    file_id: int,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    actor_kind: str = "faculty",
    is_admin_actor: bool = False,
    comment_text: str,
    attachments: list[dict[str, Any]] | None = None,
) -> FileMovement:
    """Returns an active circulated file back to the sender of the latest movement."""
    valid_comment = _validate_return_inputs(actor_kind, is_admin_actor, comment_text)
    with transaction.atomic():
        try:
            file_obj = File.objects.select_for_update().get(id=file_id)
        except File.DoesNotExist as e:
            raise NotFoundError(f"File #{file_id} was not found.") from e

        _validate_return_custody(file_obj, actor_user_id)
        prev_id, prev_name, prev_role = _resolve_return_recipient(file_obj, actor_user_id)
        last_seq = (
            FileMovement.objects.filter(file=file_obj)
            .order_by("-sequence").values_list("sequence", flat=True).first() or 0
        )
        target_status = transition_state(file_obj.status, ACTION_RETURN)
        movement = _persist_return_movement(
            file_obj, last_seq + 1, actor_user_id, actor_username, actor_role,
            prev_id, prev_name, prev_role, valid_comment, attachments, target_status,
        )
        trigger_notification(
            event_type="FILE_RETURNED", recipient_user_id=prev_id,
            payload={
                "file_id": file_obj.id, "reference_number": file_obj.reference_number,
                "returned_by": actor_username,
            },
        )
    return movement
