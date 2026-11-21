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

    with transaction.atomic():
        try:
            file_obj = File.objects.select_for_update().get(id=file_id)
        except File.DoesNotExist as e:
            raise NotFoundError(f"File #{file_id} was not found.") from e

        if file_obj.status == STATE_ARCHIVED:
            raise ConflictError(
                "Archived files cannot be forwarded.", code="archived_file_immutable"
            )

        if file_obj.status == STATE_DISCARDED:
            raise ConflictError(
                "Discarded files cannot be forwarded.", code="discarded_file_invalid"
            )

        if file_obj.current_holder_user_id != actor_user_id:
            raise PermissionDeniedError(
                "You are not the current holder of this file and cannot forward it.",
                code="not_current_holder",
            )

        action = ACTION_SEND_INITIAL if file_obj.status == STATE_DRAFT else ACTION_FORWARD
        try:
            target_status = transition_state(file_obj.status, action)
        except ArchivedFileModificationProhibitedError as e:
            raise ConflictError(str(e), code="archived_file_immutable") from e
        except FtsDomainError as e:
            raise ConflictError(str(e), code="invalid_state_transition") from e

        last_seq = (
            FileMovement.objects.filter(file=file_obj)
            .order_by("-sequence")
            .values_list("sequence", flat=True)
            .first()
            or 0
        )
        next_seq = last_seq + 1

        movement = FileMovement.objects.create(
            file=file_obj,
            sequence=next_seq,
            movement_type="FORWARD",
            from_user_id=actor_user_id,
            from_username=actor_username,
            from_role=actor_role,
            to_user_id=valid_to_id,
            to_username=to_username,
            to_role=to_role,
        )

        FileComment.objects.create(
            file=file_obj,
            movement=movement,
            author_user_id=actor_user_id,
            author_username=actor_username,
            author_role=actor_role,
            comment_text=valid_comment,
        )

        if attachments:
            for att in attachments:
                FileAttachment.objects.create(
                    file=file_obj,
                    movement=movement,
                    uploader_user_id=actor_user_id,
                    uploader_username=actor_username,
                    file_name=att.get("file_name", "attachment"),
                    file_url=att.get("file_url", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", ""),
                )

        file_obj.status = target_status
        file_obj.current_holder_user_id = valid_to_id
        file_obj.current_holder_username = to_username
        file_obj.current_holder_role = to_role
        file_obj.save(
            update_fields=[
                "status",
                "current_holder_user_id",
                "current_holder_username",
                "current_holder_role",
                "updated_at",
            ]
        )

        record_audit(
            file_id=file_obj.id,
            action="FILE_FORWARDED",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            actor_role=actor_role,
            details={
                "sequence": next_seq,
                "to_user_id": valid_to_id,
                "to_username": to_username,
                "status": target_status,
            },
        )

        trigger_notification(
            event_type="FILE_RECEIVED",
            recipient_user_id=valid_to_id,
            payload={
                "file_id": file_obj.id,
                "reference_number": file_obj.reference_number,
                "from": actor_username,
            },
        )
        trigger_notification(
            event_type="FILE_FORWARDED",
            recipient_user_id=actor_user_id,
            payload={
                "file_id": file_obj.id,
                "reference_number": file_obj.reference_number,
                "to": to_username,
            },
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
    try:
        validate_employee_operational_actor(actor_kind, is_admin_actor)
        valid_comment = validate_mandatory_comment(comment_text)
    except MandatoryCommentMissingError as e:
        raise BadRequestError(str(e), code="mandatory_comment_missing") from e
    except SystemAdminOperationalActionProhibitedError as e:
        raise PermissionDeniedError(str(e), code="admin_operational_action_prohibited") from e
    except FtsDomainError as e:
        raise BadRequestError(str(e), code="fts_validation_error") from e

    with transaction.atomic():
        try:
            file_obj = File.objects.select_for_update().get(id=file_id)
        except File.DoesNotExist as e:
            raise NotFoundError(f"File #{file_id} was not found.") from e

        if file_obj.status != STATE_CIRCULATED:
            raise ConflictError(
                "Only active circulated files can be returned.", code="file_not_circulated"
            )

        if file_obj.current_holder_user_id != actor_user_id:
            raise PermissionDeniedError(
                "You are not the current holder of this file and cannot return it.",
                code="not_current_holder",
            )

        last_movement = FileMovement.objects.filter(file=file_obj).order_by("-sequence").first()
        if not last_movement:
            raise ConflictError(
                "No movement record exists to identify previous sender.", code="no_previous_sender"
            )

        prev_sender_id = last_movement.from_user_id
        prev_sender_name = last_movement.from_username
        prev_sender_role = last_movement.from_role

        if prev_sender_id == actor_user_id:
            prior = (
                FileMovement.objects.filter(file=file_obj, to_user_id=actor_user_id)
                .order_by("-sequence")
                .first()
            )
            if prior:
                prev_sender_id = prior.from_user_id
                prev_sender_name = prior.from_username
                prev_sender_role = prior.from_role

        target_status = transition_state(file_obj.status, ACTION_RETURN)
        next_seq = last_movement.sequence + 1

        movement = FileMovement.objects.create(
            file=file_obj,
            sequence=next_seq,
            movement_type="RETURN",
            from_user_id=actor_user_id,
            from_username=actor_username,
            from_role=actor_role,
            to_user_id=prev_sender_id,
            to_username=prev_sender_name,
            to_role=prev_sender_role,
        )

        FileComment.objects.create(
            file=file_obj,
            movement=movement,
            author_user_id=actor_user_id,
            author_username=actor_username,
            author_role=actor_role,
            comment_text=valid_comment,
        )

        if attachments:
            for att in attachments:
                FileAttachment.objects.create(
                    file=file_obj,
                    movement=movement,
                    uploader_user_id=actor_user_id,
                    uploader_username=actor_username,
                    file_name=att.get("file_name", "attachment"),
                    file_url=att.get("file_url", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", ""),
                )

        file_obj.status = target_status
        file_obj.current_holder_user_id = prev_sender_id
        file_obj.current_holder_username = prev_sender_name
        file_obj.current_holder_role = prev_sender_role
        file_obj.save(
            update_fields=[
                "status",
                "current_holder_user_id",
                "current_holder_username",
                "current_holder_role",
                "updated_at",
            ]
        )

        record_audit(
            file_id=file_obj.id,
            action="FILE_RETURNED",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            actor_role=actor_role,
            details={
                "sequence": next_seq,
                "to_user_id": prev_sender_id,
                "to_username": prev_sender_name,
            },
        )

        trigger_notification(
            event_type="FILE_RETURNED",
            recipient_user_id=prev_sender_id,
            payload={
                "file_id": file_obj.id,
                "reference_number": file_obj.reference_number,
                "returned_by": actor_username,
            },
        )

    return movement
