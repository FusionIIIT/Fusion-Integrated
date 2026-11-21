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


def _validate_create_actor(
    actor_kind: str,
    is_admin_actor: bool,
    comment_text: str,
    is_draft: bool,
    recipient_user_id: int | None,
) -> str:
    """Validates actor permissions and input parameters for file creation."""
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
    else:
        return valid_comment


def _attach_creation_files(
    file_obj: File,
    movement: FileMovement,
    actor_user_id: int,
    actor_username: str,
    attachments: list[dict[str, Any]] | None,
) -> None:
    """Attaches uploaded supporting documents to the creation movement."""
    if not attachments:
        return
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


def _create_file_row(
    ref_no: str,
    subject: str,
    description: str,
    target_status: str,
    actor_id: int,
    actor_name: str,
    actor_role: str,
    holder_id: int,
    holder_name: str,
    holder_role: str,
) -> File:
    """Creates the initial file database row."""
    return File.objects.create(
        reference_number=ref_no,
        subject=subject.strip(),
        description=description.strip(),
        status=target_status,
        owner_user_id=actor_id,
        owner_username=actor_name,
        owner_role=actor_role,
        current_holder_user_id=holder_id,
        current_holder_username=holder_name,
        current_holder_role=holder_role,
    )


def _persist_file_creation(
    *,
    ref_no: str,
    subject: str,
    description: str,
    target_status: str,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    holder_id: int,
    holder_name: str,
    holder_role: str,
    valid_comment: str,
    attachments: list[dict[str, Any]] | None,
) -> File:
    """Persists file, initial movement, comment, and attachments in one transaction."""
    with transaction.atomic():
        file_obj = _create_file_row(
            ref_no, subject, description, target_status,
            actor_user_id, actor_username, actor_role, holder_id, holder_name, holder_role,
        )
        movement = FileMovement.objects.create(
            file=file_obj, sequence=1, movement_type="CREATION",
            from_user_id=actor_user_id, from_username=actor_username, from_role=actor_role,
            to_user_id=holder_id, to_username=holder_name, to_role=holder_role,
        )
        FileComment.objects.create(
            file=file_obj, movement=movement, author_user_id=actor_user_id,
            author_username=actor_username, author_role=actor_role, comment_text=valid_comment,
        )
        _attach_creation_files(file_obj, movement, actor_user_id, actor_username, attachments)
        record_audit(
            file_id=file_obj.id, action="FILE_CREATED", actor_user_id=actor_user_id,
            actor_username=actor_username, actor_role=actor_role,
            details={"status": target_status, "reference_number": ref_no},
        )
        return file_obj


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
    valid_comment = _validate_create_actor(
        actor_kind, is_admin_actor, comment_text, is_draft, recipient_user_id
    )
    action = ACTION_CREATE_DRAFT if is_draft else ACTION_CREATE_AND_CIRCULATE
    target_status = transition_state(None, action)
    holder_id = actor_user_id if is_draft else (recipient_user_id or actor_user_id)
    holder_name = actor_username if is_draft else (recipient_username or actor_username)
    holder_role = actor_role if is_draft else (recipient_role or actor_role)
    ref_no = generate_reference_number()

    file_obj = _persist_file_creation(
        ref_no=ref_no,
        subject=subject,
        description=description,
        target_status=target_status,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        actor_role=actor_role,
        holder_id=holder_id,
        holder_name=holder_name,
        holder_role=holder_role,
        valid_comment=valid_comment,
        attachments=attachments,
    )
    if not is_draft and recipient_user_id:
        trigger_notification(
            event_type="FILE_RECEIVED",
            recipient_user_id=recipient_user_id,
            payload={"file_id": file_obj.id, "reference_number": ref_no, "from": actor_username},
        )
    return file_obj


def _apply_draft_updates(
    file_obj: File,
    subject: str | None,
    description: str | None,
    comment_text: str | None,
    attachments: list[dict[str, Any]] | None,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
) -> list[str]:
    """Applies modifications to draft file fields, comments, and attachments."""
    update_fields = ["updated_at"]
    if subject is not None:
        file_obj.subject = subject.strip()
        update_fields.append("subject")
    if description is not None:
        file_obj.description = description.strip()
        update_fields.append("description")
    file_obj.save(update_fields=update_fields)

    creation_movement = file_obj.movements.filter(sequence=1).first()
    if comment_text is not None:
        valid_comment = validate_mandatory_comment(comment_text)
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
    return update_fields


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
            raise PermissionDeniedError(
                "Only the draft owner may edit the draft. "
                "Contact the draft creator or request ownership transfer."
            )
        if file_obj.status != STATE_DRAFT:
            raise ConflictError(
                "Only draft files can be edited before circulation. "
                "Circulated files must be forwarded with remarks instead."
            )

        transition_state(file_obj.status, ACTION_EDIT_DRAFT)
        update_fields = _apply_draft_updates(
            file_obj, subject, description, comment_text, attachments,
            actor_user_id, actor_username, actor_role
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
            raise PermissionDeniedError(
                "Only the draft owner may discard the draft. "
                "Contact the file creator to request deletion."
            )

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
