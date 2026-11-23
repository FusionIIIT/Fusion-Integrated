"""Core file management service for File Tracking System (all writes).

One transactional choke point per state change. All movement takes
select_for_update, refuses terminal states, validates actor role,
updates holder, logs movements, and records immutable audits.
"""

from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.filetracking.domain.entities import FileEvent, FileStatus, MovementAction
from modules.filetracking.domain.errors import (
    CommentRequiredError,
    DraftDiscardError,
    FileArchivedError,
    InvalidAttachmentError,
    InvalidRecipientError,
    StateTransitionError,
)
from modules.filetracking.domain.rules import (
    validate_attachment,
    validate_draft_for_discard,
    validate_file_not_archived,
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
    validate_owner_for_archive,
    validate_return_recipient,
)
from modules.filetracking.domain.state_machine import get_next_state
from modules.filetracking.models import FileAttachment, FileMovement, TrackedFile
from modules.filetracking.services.audit import record_audit
from modules.filetracking.services.notifications import trigger_file_notification


def generate_file_number() -> str:
    """Generate institutional file number format FTS/<YEAR>/<SEQ>."""
    year = timezone.now().year
    count = TrackedFile.objects.filter(file_number__startswith=f"FTS/{year}/").count() + 1
    return f"FTS/{year}/{count:05d}"


def create_file(
    *,
    creator_user_id: int,
    creator_designation: str,
    subject: str,
    initial_comment: str,
    is_draft: bool = False,
    recipient_user_id: int | None = None,
    recipient_designation: str = "",
    attachments: list[dict[str, Any]] | None = None,
    ip_address: str | None = None,
) -> TrackedFile:
    """Create a new file as draft or directly submit into circulation (FTS-UC-001)."""
    if not subject or not subject.strip():
        raise BadRequestError("A subject is required to create a file.", code="subject_required")

    try:
        validate_initial_comment(initial_comment)
    except CommentRequiredError as exc:
        raise BadRequestError(exc.message, code="comment_required") from exc

    if not is_draft:
        if not recipient_user_id:
            raise BadRequestError(
                "A recipient must be specified to circulate a file.",
                code="recipient_required",
            )
        try:
            validate_forward_recipient(creator_user_id, recipient_user_id)
        except InvalidRecipientError as exc:
            raise BadRequestError(exc.message, code="invalid_recipient") from exc

    with transaction.atomic():
        file_number = generate_file_number()
        status = FileStatus.DRAFT if is_draft else FileStatus.CIRCULATING
        holder_id = None if is_draft else recipient_user_id
        holder_desig = "" if is_draft else recipient_designation

        file = TrackedFile.objects.create(
            file_number=file_number,
            subject=subject.strip(),
            description=initial_comment.strip(),
            status=status,
            created_by_user_id=creator_user_id,
            creator_designation=creator_designation,
            current_holder_user_id=holder_id,
            current_holder_designation=holder_desig,
            is_archived=False,
        )

        first_movement = None
        if not is_draft:
            first_movement = FileMovement.objects.create(
                file=file,
                sequence_number=1,
                action=MovementAction.CREATED,
                sender_user_id=creator_user_id,
                sender_designation=creator_designation,
                receiver_user_id=recipient_user_id,
                receiver_designation=recipient_designation,
                comment=initial_comment.strip(),
            )

        if attachments:
            for att in attachments:
                try:
                    validate_attachment(
                        file_name=att.get("file_name", "document"),
                        file_size=att.get("file_size", 0),
                        mime_type=att.get("mime_type", "application/pdf"),
                    )
                except InvalidAttachmentError as exc:
                    raise BadRequestError(exc.message, code="invalid_attachment") from exc

                FileAttachment.objects.create(
                    file=file,
                    movement=first_movement,
                    uploaded_by_user_id=creator_user_id,
                    uploader_designation=creator_designation,
                    file_name=att.get("file_name", "document"),
                    file_path=att.get("file_path") or att.get("storage_key") or "files/doc",
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/pdf"),
                )

        record_audit(
            action="file.create_draft" if is_draft else "file.create_and_circulate",
            actor_user_id=creator_user_id,
            actor_designation=creator_designation,
            file_id=file.id,
            payload={
                "file_number": file.file_number,
                "status": file.status,
                "recipient_user_id": recipient_user_id,
            },
            ip_address=ip_address,
        )

        if not is_draft and recipient_user_id:
            trigger_file_notification(
                topic="file.received",
                recipient_user_id=recipient_user_id,
                file_id=file.id,
                file_number=file.file_number,
                subject=file.subject,
                message=f"You received a new file: {file.file_number} - {file.subject}",
                actor_user_id=creator_user_id,
                actor_designation=creator_designation,
            )

        return file


def update_draft(
    *,
    file_id: int,
    actor_user_id: int,
    actor_designation: str,
    subject: str | None = None,
    description: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    ip_address: str | None = None,
) -> TrackedFile:
    """Edit an uncirculated draft file (FTS-UC-002)."""
    with transaction.atomic():
        try:
            file = TrackedFile.objects.select_for_update().get(id=file_id)
        except TrackedFile.DoesNotExist as exc:
            raise NotFoundError("Draft file not found.", code="file_not_found") from exc

        if file.created_by_user_id != actor_user_id:
            raise PermissionDeniedError(
                "Only the draft owner can edit this draft.",
                code="forbidden",
            )

        if file.status != FileStatus.DRAFT:
            raise ConflictError(
                "Circulated files cannot be edited as drafts.",
                code="cannot_edit_circulated_file",
            )

        get_next_state(file.status, FileEvent.UPDATE_DRAFT, "OWNER")

        if subject is not None:
            if not subject.strip():
                raise BadRequestError("Subject cannot be empty.", code="subject_required")
            file.subject = subject.strip()

        if description is not None:
            if not description.strip():
                raise BadRequestError("Description cannot be empty.", code="description_required")
            file.description = description.strip()

        file.save(update_fields=["subject", "description", "updated_at"])

        if attachments:
            for att in attachments:
                try:
                    validate_attachment(
                        file_name=att.get("file_name", "document"),
                        file_size=att.get("file_size", 0),
                        mime_type=att.get("mime_type", "application/pdf"),
                    )
                except InvalidAttachmentError as exc:
                    raise BadRequestError(exc.message, code="invalid_attachment") from exc
                FileAttachment.objects.create(
                    file=file,
                    movement=None,
                    uploaded_by_user_id=actor_user_id,
                    uploader_designation=actor_designation,
                    file_name=att.get("file_name", "document"),
                    file_path=att.get("file_path") or att.get("storage_key") or "files/doc",
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/pdf"),
                )

        record_audit(
            action="file.update_draft",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
            file_id=file.id,
            payload={"updated_fields": ["subject", "description"]},
            ip_address=ip_address,
        )
        return file


def discard_draft(
    *,
    file_id: int,
    actor_user_id: int,
    actor_designation: str,
    ip_address: str | None = None,
) -> None:
    """Discard an uncirculated draft file (BR-FTS-005, FTS-UC-002)."""
    with transaction.atomic():
        try:
            file = TrackedFile.objects.select_for_update().get(id=file_id)
        except TrackedFile.DoesNotExist as exc:
            raise NotFoundError("Draft file not found.", code="file_not_found") from exc

        if file.created_by_user_id != actor_user_id:
            raise PermissionDeniedError(
                "Only the draft owner can discard this draft.",
                code="forbidden",
            )

        try:
            validate_draft_for_discard(file.status)
        except DraftDiscardError as exc:
            raise ConflictError(exc.message, code="cannot_discard_circulated_file") from exc

        get_next_state(file.status, FileEvent.DISCARD_DRAFT, "OWNER")

        file_number = file.file_number
        file.attachments.all().delete()
        file.delete()

        record_audit(
            action="file.discard_draft",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
            file_id=file_id,
            payload={"file_number": file_number},
            ip_address=ip_address,
        )


def forward_file(
    *,
    file_id: int,
    actor_user_id: int,
    actor_designation: str,
    recipient_user_id: int,
    recipient_designation: str,
    comment: str,
    attachments: list[dict[str, Any]] | None = None,
    ip_address: str | None = None,
) -> FileMovement:
    """Forward an active file to another employee (BR-FTS-006, BR-FTS-007, FTS-UC-003)."""
    try:
        validate_movement_comment(comment)
    except CommentRequiredError as exc:
        raise BadRequestError(exc.message, code="comment_required") from exc

    try:
        validate_forward_recipient(actor_user_id, recipient_user_id)
    except InvalidRecipientError as exc:
        raise BadRequestError(exc.message, code="invalid_recipient") from exc

    with transaction.atomic():
        try:
            file = TrackedFile.objects.select_for_update().get(id=file_id)
        except TrackedFile.DoesNotExist as exc:
            raise NotFoundError("File not found.", code="file_not_found") from exc

        try:
            validate_file_not_archived(file.status)
        except FileArchivedError as exc:
            raise ConflictError(exc.message, code="file_already_archived") from exc

        if file.status == FileStatus.DRAFT:
            # First send from draft
            if file.created_by_user_id != actor_user_id:
                raise PermissionDeniedError(
                    "Only the owner can circulate a draft.",
                    code="forbidden",
                )
            actor_role = "OWNER"
            event = FileEvent.SUBMIT_INITIAL
        else:
            if file.current_holder_user_id != actor_user_id:
                raise PermissionDeniedError(
                    "You are not the current holder of this file and cannot forward it.",
                    code="not_current_holder",
                )
            actor_role = "CURRENT_HOLDER"
            event = FileEvent.FORWARD

        try:
            next_state = get_next_state(file.status, event, actor_role)
        except StateTransitionError as exc:
            raise ConflictError(exc.message, code="illegal_state_transition") from exc

        seq = file.movements.count() + 1
        movement = FileMovement.objects.create(
            file=file,
            sequence_number=seq,
            action=MovementAction.FORWARDED,
            sender_user_id=actor_user_id,
            sender_designation=actor_designation,
            receiver_user_id=recipient_user_id,
            receiver_designation=recipient_designation,
            comment=comment.strip(),
        )

        file.status = next_state
        file.current_holder_user_id = recipient_user_id
        file.current_holder_designation = recipient_designation
        file.save(
            update_fields=[
                "status",
                "current_holder_user_id",
                "current_holder_designation",
                "updated_at",
            ]
        )

        if attachments:
            for att in attachments:
                try:
                    validate_attachment(
                        file_name=att.get("file_name", "document"),
                        file_size=att.get("file_size", 0),
                        mime_type=att.get("mime_type", "application/pdf"),
                    )
                except InvalidAttachmentError as exc:
                    raise BadRequestError(exc.message, code="invalid_attachment") from exc
                FileAttachment.objects.create(
                    file=file,
                    movement=movement,
                    uploaded_by_user_id=actor_user_id,
                    uploader_designation=actor_designation,
                    file_name=att.get("file_name", "document"),
                    file_path=att.get("file_path") or att.get("storage_key") or "files/doc",
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/pdf"),
                )

        record_audit(
            action="file.forward",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
            file_id=file.id,
            payload={
                "movement_seq": seq,
                "recipient_user_id": recipient_user_id,
                "recipient_designation": recipient_designation,
            },
            ip_address=ip_address,
        )

        trigger_file_notification(
            topic="file.forwarded",
            recipient_user_id=recipient_user_id,
            file_id=file.id,
            file_number=file.file_number,
            subject=file.subject,
            message=f"File {file.file_number} has been forwarded to you by {actor_designation}.",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
        )

        return movement


def return_file(
    *,
    file_id: int,
    actor_user_id: int,
    actor_designation: str,
    comment: str,
    attachments: list[dict[str, Any]] | None = None,
    ip_address: str | None = None,
) -> FileMovement:
    """Return an active received file to previous sender (BR-FTS-006, BR-FTS-007, FTS-UC-004)."""
    try:
        validate_movement_comment(comment)
    except CommentRequiredError as exc:
        raise BadRequestError(exc.message, code="comment_required") from exc

    with transaction.atomic():
        try:
            file = TrackedFile.objects.select_for_update().get(id=file_id)
        except TrackedFile.DoesNotExist as exc:
            raise NotFoundError("File not found.", code="file_not_found") from exc

        try:
            validate_file_not_archived(file.status)
        except FileArchivedError as exc:
            raise ConflictError(exc.message, code="file_already_archived") from exc

        if file.status != FileStatus.CIRCULATING:
            raise ConflictError(
                "Only circulating files may be returned.",
                code="file_not_circulating",
            )

        if file.current_holder_user_id != actor_user_id:
            raise PermissionDeniedError(
                "You are not the current holder of this file and cannot return it.",
                code="not_current_holder",
            )

        last_movement = file.movements.order_by("-sequence_number").first()
        if not last_movement:
            raise ConflictError(
                "Cannot return a file that has no recorded movement history.",
                code="no_previous_sender",
            )

        target_recipient_id = last_movement.sender_user_id
        target_designation = last_movement.sender_designation

        try:
            validate_return_recipient(last_movement.sender_user_id, target_recipient_id)
        except InvalidRecipientError as exc:
            raise BadRequestError(exc.message, code="invalid_return_target") from exc

        next_state = get_next_state(file.status, FileEvent.RETURN, "CURRENT_HOLDER")

        seq = file.movements.count() + 1
        movement = FileMovement.objects.create(
            file=file,
            sequence_number=seq,
            action=MovementAction.RETURNED,
            sender_user_id=actor_user_id,
            sender_designation=actor_designation,
            receiver_user_id=target_recipient_id,
            receiver_designation=target_designation,
            comment=comment.strip(),
        )

        file.status = next_state
        file.current_holder_user_id = target_recipient_id
        file.current_holder_designation = target_designation
        file.save(
            update_fields=[
                "status",
                "current_holder_user_id",
                "current_holder_designation",
                "updated_at",
            ]
        )

        if attachments:
            for att in attachments:
                try:
                    validate_attachment(
                        file_name=att.get("file_name", "document"),
                        file_size=att.get("file_size", 0),
                        mime_type=att.get("mime_type", "application/pdf"),
                    )
                except InvalidAttachmentError as exc:
                    raise BadRequestError(exc.message, code="invalid_attachment") from exc
                FileAttachment.objects.create(
                    file=file,
                    movement=movement,
                    uploaded_by_user_id=actor_user_id,
                    uploader_designation=actor_designation,
                    file_name=att.get("file_name", "document"),
                    file_path=att.get("file_path") or att.get("storage_key") or "files/doc",
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/pdf"),
                )

        record_audit(
            action="file.return",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
            file_id=file.id,
            payload={
                "movement_seq": seq,
                "returned_to_user_id": target_recipient_id,
            },
            ip_address=ip_address,
        )

        trigger_file_notification(
            topic="file.returned",
            recipient_user_id=target_recipient_id,
            file_id=file.id,
            file_number=file.file_number,
            subject=file.subject,
            message=f"File {file.file_number} has been returned to you by {actor_designation}.",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
        )

        return movement


def archive_file(
    *,
    file_id: int,
    actor_user_id: int,
    actor_designation: str,
    comment: str | None = None,
    ip_address: str | None = None,
) -> TrackedFile:
    """Archive a completed circulated file (owner only per BR-FTS-012, FTS-UC-007)."""
    with transaction.atomic():
        try:
            file = TrackedFile.objects.select_for_update().get(id=file_id)
        except TrackedFile.DoesNotExist as exc:
            raise NotFoundError("File not found.", code="file_not_found") from exc

        if file.status == FileStatus.ARCHIVED or file.is_archived:
            raise ConflictError("File is already archived.", code="file_already_archived")

        if file.status != FileStatus.CIRCULATING:
            raise ConflictError(
                "Only circulating files can be archived.",
                code="file_not_circulating",
            )

        try:
            validate_owner_for_archive(file.created_by_user_id, actor_user_id)
        except StateTransitionError as exc:
            raise PermissionDeniedError(exc.message, code="forbidden") from exc

        next_state = get_next_state(file.status, FileEvent.ARCHIVE, "OWNER")

        seq = file.movements.count() + 1
        FileMovement.objects.create(
            file=file,
            sequence_number=seq,
            action=MovementAction.ARCHIVED,
            sender_user_id=actor_user_id,
            sender_designation=actor_designation,
            receiver_user_id=actor_user_id,
            receiver_designation=actor_designation,
            comment=comment.strip() if comment else "File archived upon completion.",
        )

        file.status = next_state
        file.is_archived = True
        file.archived_at = timezone.now()
        file.current_holder_user_id = None
        file.current_holder_designation = ""
        file.save(
            update_fields=[
                "status",
                "is_archived",
                "archived_at",
                "current_holder_user_id",
                "current_holder_designation",
                "updated_at",
            ]
        )

        record_audit(
            action="file.archive",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
            file_id=file.id,
            payload={"archived_at": file.archived_at.isoformat()},
            ip_address=ip_address,
        )

        trigger_file_notification(
            topic="file.archived",
            recipient_user_id=file.created_by_user_id,
            file_id=file.id,
            file_number=file.file_number,
            subject=file.subject,
            message=f"File {file.file_number} has been archived.",
            actor_user_id=actor_user_id,
            actor_designation=actor_designation,
        )

        return file
