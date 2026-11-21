"""File creation, draft update, and draft discard services for FTS."""
from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.fts.domain.entities import (
    validate_employee_operational_actor,
    validate_mandatory_comment,
    validate_recipient,
)
from modules.fts.domain.errors import (
    CirculatedFileDeletionProhibitedError,
    FtsDomainError,
    InvalidRecipientError,
    MandatoryCommentMissingError,
    SystemAdminOperationalActionProhibitedError,
)
from modules.fts.domain.state_machine import (
    ACTION_CREATE_AND_CIRCULATE,
    ACTION_CREATE_DRAFT,
    ACTION_DISCARD_DRAFT,
    ACTION_EDIT_DRAFT,
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


def generate_reference_number() -> str:
    """Generates a unique institutional reference number."""
    now = timezone.now()
    suffix = uuid.uuid4().hex[:6].upper()
    return f"FTS-{now.year}{now.month:02d}{now.day:02d}-{suffix}"


def create_file(
    *,
    subject: str,
    description: str = "",
    comment_text: str,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    actor_kind: str = "faculty",
    is_admin_actor: bool = False,
    is_draft: bool = False,
    recipient_user_id: int | None = None,
    recipient_username: str = "",
    recipient_role: str = "",
    attachments: list[dict[str, Any]] | None = None,
) -> File:
    """Creates a new institutional file as a draft or immediately circulated file."""
    try:
        validate_employee_operational_actor(actor_kind, is_admin_actor)
        valid_comment = validate_mandatory_comment(comment_text)
        if not is_draft:
            validate_recipient(recipient_user_id)
    except MandatoryCommentMissingError as e:
        raise BadRequestError(str(e), code="mandatory_comment_missing") from e
    except InvalidRecipientError as e:
        raise BadRequestError(str(e), code="invalid_recipient") from e
    except SystemAdminOperationalActionProhibitedError as e:
        raise PermissionDeniedError(str(e), code="admin_operational_action_prohibited") from e
    except FtsDomainError as e:
        raise BadRequestError(str(e), code="fts_validation_error") from e

    action = ACTION_CREATE_DRAFT if is_draft else ACTION_CREATE_AND_CIRCULATE
    target_status = transition_state(None, action)

    if is_draft:
        holder_id = actor_user_id
        holder_name = actor_username
        holder_role = actor_role
    else:
        holder_id = recipient_user_id or actor_user_id
        holder_name = recipient_username or actor_username
        holder_role = recipient_role or actor_role

    ref_no = generate_reference_number()

    with transaction.atomic():
        file_obj = File.objects.create(
            reference_number=ref_no,
            subject=subject.strip(),
            description=description.strip(),
            status=target_status,
            owner_user_id=actor_user_id,
            owner_username=actor_username,
            owner_role=actor_role,
            current_holder_user_id=holder_id,
            current_holder_username=holder_name,
            current_holder_role=holder_role,
        )

        movement = FileMovement.objects.create(
            file=file_obj,
            sequence=1,
            movement_type="CREATION",
            from_user_id=actor_user_id,
            from_username=actor_username,
            from_role=actor_role,
            to_user_id=holder_id,
            to_username=holder_name,
            to_role=holder_role,
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

        record_audit(
            file_id=file_obj.id,
            action="FILE_CREATED",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            actor_role=actor_role,
            details={"status": target_status, "reference_number": ref_no},
        )

        if not is_draft and recipient_user_id:
            trigger_notification(
                event_type="FILE_RECEIVED",
                recipient_user_id=recipient_user_id,
                payload={
                    "file_id": file_obj.id,
                    "reference_number": ref_no,
                    "from": actor_username,
                },
            )

    return file_obj


def update_draft(
    *,
    file_id: int,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    subject: str | None = None,
    description: str | None = None,
    comment_text: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> File:
    """Updates an existing pre-circulation draft."""
    with transaction.atomic():
        try:
            file_obj = File.objects.select_for_update().get(id=file_id)
        except File.DoesNotExist as e:
            raise NotFoundError(f"File #{file_id} was not found.") from e

        if file_obj.owner_user_id != actor_user_id:
            raise PermissionDeniedError("Only the draft owner may edit the draft.")

        if file_obj.status != STATE_DRAFT:
            raise ConflictError("Only draft files can be edited before circulation.")

        transition_state(file_obj.status, ACTION_EDIT_DRAFT)

        update_fields = ["updated_at"]
        if subject is not None:
            file_obj.subject = subject.strip()
            update_fields.append("subject")
        if description is not None:
            file_obj.description = description.strip()
            update_fields.append("description")

        file_obj.save(update_fields=update_fields)

        if comment_text is not None:
            valid_comment = validate_mandatory_comment(comment_text)
            creation_movement = file_obj.movements.filter(sequence=1).first()
            first_comment = file_obj.comments.filter(movement=creation_movement).first()
            if first_comment:
                first_comment.comment_text = valid_comment
                first_comment.save(update_fields=["comment_text", "updated_at"])
            else:
                FileComment.objects.create(
                    file=file_obj,
                    movement=creation_movement,
                    author_user_id=actor_user_id,
                    author_username=actor_username,
                    author_role=actor_role,
                    comment_text=valid_comment,
                )

        if attachments is not None:
            creation_movement = file_obj.movements.filter(sequence=1).first()
            for att in attachments:
                FileAttachment.objects.create(
                    file=file_obj,
                    movement=creation_movement,
                    uploader_user_id=actor_user_id,
                    uploader_username=actor_username,
                    file_name=att.get("file_name", "attachment"),
                    file_url=att.get("file_url", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", ""),
                )

        record_audit(
            file_id=file_obj.id,
            action="DRAFT_UPDATED",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            actor_role=actor_role,
            details={"updated_fields": update_fields},
        )

    return file_obj


def discard_draft(
    *,
    file_id: int,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
) -> File:
    """Discards an uncirculated draft before submission."""
    with transaction.atomic():
        try:
            file_obj = File.objects.select_for_update().get(id=file_id)
        except File.DoesNotExist as e:
            raise NotFoundError(f"File #{file_id} was not found.") from e

        if file_obj.owner_user_id != actor_user_id:
            raise PermissionDeniedError("Only the draft owner may discard the draft.")

        try:
            target_status = transition_state(file_obj.status, ACTION_DISCARD_DRAFT)
        except CirculatedFileDeletionProhibitedError as e:
            raise ConflictError(str(e), code="circulated_deletion_prohibited") from e
        except FtsDomainError as e:
            raise ConflictError(str(e), code="invalid_state_transition") from e

        file_obj.status = target_status
        file_obj.save(update_fields=["status", "updated_at"])

        record_audit(
            file_id=file_obj.id,
            action="DRAFT_DISCARDED",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            actor_role=actor_role,
            details={"status": STATE_DISCARDED},
        )

    return file_obj
