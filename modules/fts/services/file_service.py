"""FTS file lifecycle and movement services (CFR-FTS-001..012, BR-FTS-001..014)."""
from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.fts.domain import rules, state_machine
from modules.fts.models import (
    FileAttachment,
    FileComment,
    FileMovement,
    FTSAuditLog,
    FTSFile,
)


def _generate_file_id() -> str:
    year = timezone.now().year
    suffix = uuid.uuid4().hex[:6].upper()
    return f"FTS-{year}-{suffix}"


def create_file(
    *,
    subject: str,
    description: str = "",
    initial_comment: str,
    creator_id: int,
    creator_designation: str = "",
    is_draft: bool = False,
    receiver_id: int | None = None,
    receiver_designation: str = "",
    attachments: list[dict[str, Any]] | None = None,
    is_employee: bool = True,
    is_system_admin: bool = False,
) -> FTSFile:
    """Create a new file either directly into circulation or as a draft."""
    try:
        rules.validate_operational_role(is_employee, is_system_admin)
        rules.validate_initial_comment(initial_comment)
    except rules.FTSValidationError as exc:
        if exc.code == "admin_operational_forbidden":
            raise PermissionDeniedError(exc.args[0], code=exc.code) from exc
        raise BadRequestError(exc.args[0], code=exc.code) from exc

    if not subject or not subject.strip():
        raise BadRequestError("File subject is required.", code="subject_required")

    with transaction.atomic():
        file_id = _generate_file_id()

        if is_draft:
            file_obj = FTSFile.objects.create(
                file_id=file_id,
                subject=subject.strip(),
                description=description.strip(),
                status=state_machine.DRAFT,
                creator_id=creator_id,
                creator_designation=creator_designation,
                owner_id=creator_id,
                current_holder_id=creator_id,
                current_holder_designation=creator_designation,
            )

            FileComment.objects.create(
                file=file_obj,
                author_id=creator_id,
                author_designation=creator_designation,
                comment_text=initial_comment.strip(),
            )

            if attachments:
                for att in attachments:
                    FileAttachment.objects.create(
                        file=file_obj,
                        uploader_id=creator_id,
                        file_name=att.get("file_name", "attachment"),
                        file_path=att.get("file_path", ""),
                        file_size=att.get("file_size", 0),
                        mime_type=att.get("mime_type", "application/octet-stream"),
                    )

            FTSAuditLog.objects.create(
                file=file_obj,
                actor_id=creator_id,
                actor_role=creator_designation,
                action_type="save_draft",
                details={"file_id": file_obj.file_id, "subject": file_obj.subject},
            )
            return file_obj

        if not receiver_id:
            raise BadRequestError(
                "A recipient must be specified to circulate a file.",
                code="recipient_required",
            )
        try:
            rules.validate_forward_recipient(creator_id, receiver_id)
        except rules.FTSValidationError as exc:
            raise BadRequestError(exc.args[0], code=exc.code) from exc

        file_obj = FTSFile.objects.create(
            file_id=file_id,
            subject=subject.strip(),
            description=description.strip(),
            status=state_machine.CIRCULATING,
            creator_id=creator_id,
            creator_designation=creator_designation,
            owner_id=creator_id,
            current_holder_id=receiver_id,
            current_holder_designation=receiver_designation,
        )

        mov = FileMovement.objects.create(
            file=file_obj,
            sequence_number=1,
            sender_id=creator_id,
            sender_designation=creator_designation,
            receiver_id=receiver_id,
            receiver_designation=receiver_designation,
            action="created",
            remarks=initial_comment.strip(),
        )

        FileComment.objects.create(
            file=file_obj,
            movement=mov,
            author_id=creator_id,
            author_designation=creator_designation,
            comment_text=initial_comment.strip(),
        )

        if attachments:
            for att in attachments:
                FileAttachment.objects.create(
                    file=file_obj,
                    movement=mov,
                    uploader_id=creator_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/octet-stream"),
                )

        FTSAuditLog.objects.create(
            file=file_obj,
            actor_id=creator_id,
            actor_role=creator_designation,
            action_type="create_file",
            details={
                "file_id": file_obj.file_id,
                "receiver_id": receiver_id,
                "status": file_obj.status,
            },
        )
        return file_obj


def edit_draft(
    *,
    file_id_or_pk: str,
    user_id: int,
    subject: str | None = None,
    description: str | None = None,
    comment: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> FTSFile:
    """Edit draft file metadata, comment or attachments (FTS-UC-002, BR-FTS-005)."""
    with transaction.atomic():
        qs = FTSFile.objects.select_for_update()
        if str(file_id_or_pk).isdigit():
            file_obj = qs.filter(id=int(file_id_or_pk)).first()
        else:
            file_obj = qs.filter(file_id=file_id_or_pk).first()

        if not file_obj:
            raise NotFoundError("The requested draft file was not found.")

        if file_obj.creator_id != user_id:
            raise PermissionDeniedError("Only the draft creator may edit this draft.")

        if file_obj.status != state_machine.DRAFT:
            msg = f"Cannot edit file in '{file_obj.status}' status. Only drafts can be edited."
            raise ConflictError(msg, code="draft_status_required")

        if subject is not None:
            if not subject.strip():
                raise BadRequestError("Subject cannot be empty.", code="subject_required")
            file_obj.subject = subject.strip()

        if description is not None:
            file_obj.description = description.strip()

        file_obj.save(update_fields=["subject", "description", "updated_at"])

        if comment is not None and comment.strip():
            latest_comment = file_obj.comments.order_by("-created_at").first()
            if latest_comment:
                latest_comment.comment_text = comment.strip()
                latest_comment.save(update_fields=["comment_text"])
            else:
                FileComment.objects.create(
                    file=file_obj,
                    author_id=user_id,
                    author_designation=file_obj.creator_designation,
                    comment_text=comment.strip(),
                )

        if attachments:
            for att in attachments:
                FileAttachment.objects.create(
                    file=file_obj,
                    uploader_id=user_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/octet-stream"),
                )

        FTSAuditLog.objects.create(
            file=file_obj,
            actor_id=user_id,
            actor_role=file_obj.creator_designation,
            action_type="edit_draft",
            details={"file_id": file_obj.file_id},
        )
        return file_obj


def discard_draft(*, file_id_or_pk: str, user_id: int) -> None:
    """Discard an uncirculated draft file (FTS-UC-002, BW-FTS-07, BW-FTS-08)."""
    with transaction.atomic():
        qs = FTSFile.objects.select_for_update()
        if str(file_id_or_pk).isdigit():
            file_obj = qs.filter(id=int(file_id_or_pk)).first()
        else:
            file_obj = qs.filter(file_id=file_id_or_pk).first()

        if not file_obj:
            raise NotFoundError("The requested draft file was not found.")

        if file_obj.creator_id != user_id:
            raise PermissionDeniedError("Only the draft creator may discard this draft.")

        if file_obj.status != state_machine.DRAFT:
            msg = f"Cannot discard file in status '{file_obj.status}'. Only drafts discard."
            raise ConflictError(msg, code="draft_status_required")

        file_id_str = file_obj.file_id
        file_obj.delete()

        FTSAuditLog.objects.create(
            actor_id=user_id,
            action_type="discard_draft",
            details={"file_id": file_id_str, "status": "discarded"},
        )


def forward_file(
    *,
    file_id_or_pk: str,
    sender_id: int,
    sender_designation: str = "",
    receiver_id: int,
    receiver_designation: str = "",
    remarks: str,
    attachments: list[dict[str, Any]] | None = None,
    is_employee: bool = True,
    is_system_admin: bool = False,
) -> FileMovement:
    """Forward a file to the next employee (BW-FTS-01, BW-FTS-02, BR-FTS-006, BR-FTS-007)."""
    try:
        rules.validate_operational_role(is_employee, is_system_admin)
        rules.validate_movement_comment(remarks)
        rules.validate_forward_recipient(sender_id, receiver_id)
    except rules.FTSValidationError as exc:
        if exc.code == "admin_operational_forbidden":
            raise PermissionDeniedError(exc.args[0], code=exc.code) from exc
        raise BadRequestError(exc.args[0], code=exc.code) from exc

    with transaction.atomic():
        qs = FTSFile.objects.select_for_update()
        if str(file_id_or_pk).isdigit():
            file_obj = qs.filter(id=int(file_id_or_pk)).first()
        else:
            file_obj = qs.filter(file_id=file_id_or_pk).first()

        if not file_obj:
            raise NotFoundError("The requested file was not found.")

        if file_obj.status == state_machine.DRAFT and file_obj.creator_id == sender_id:
            file_obj.status = state_machine.CIRCULATING
        elif file_obj.status != state_machine.CIRCULATING:
            msg = f"Cannot forward file in '{file_obj.status}'. Only circulating files forward."
            raise ConflictError(msg, code="invalid_state_for_forward")
        elif file_obj.current_holder_id != sender_id:
            raise PermissionDeniedError(
                "You are not the current holder of this file and cannot forward it.",
                code="not_current_holder",
            )

        last_seq = (
            file_obj.movements.order_by("-sequence_number")
            .values_list("sequence_number", flat=True)
            .first()
            or 0
        )
        new_seq = last_seq + 1

        mov = FileMovement.objects.create(
            file=file_obj,
            sequence_number=new_seq,
            sender_id=sender_id,
            sender_designation=sender_designation,
            receiver_id=receiver_id,
            receiver_designation=receiver_designation,
            action="forwarded",
            remarks=remarks.strip(),
        )

        FileComment.objects.create(
            file=file_obj,
            movement=mov,
            author_id=sender_id,
            author_designation=sender_designation,
            comment_text=remarks.strip(),
        )

        if attachments:
            for att in attachments:
                FileAttachment.objects.create(
                    file=file_obj,
                    movement=mov,
                    uploader_id=sender_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/octet-stream"),
                )

        file_obj.current_holder_id = receiver_id
        file_obj.current_holder_designation = receiver_designation
        file_obj.save(update_fields=[
            "status",
            "current_holder_id",
            "current_holder_designation",
            "updated_at",
        ])

        FTSAuditLog.objects.create(
            file=file_obj,
            actor_id=sender_id,
            actor_role=sender_designation,
            action_type="forward_file",
            details={
                "file_id": file_obj.file_id,
                "sequence": new_seq,
                "receiver_id": receiver_id,
            },
        )
        return mov


def return_file(
    *,
    file_id_or_pk: str,
    sender_id: int,
    sender_designation: str = "",
    remarks: str,
    attachments: list[dict[str, Any]] | None = None,
    is_employee: bool = True,
    is_system_admin: bool = False,
) -> FileMovement:
    """Return a received file to its previous sender (BW-FTS-03, BR-FTS-006, BR-FTS-007)."""
    try:
        rules.validate_operational_role(is_employee, is_system_admin)
        rules.validate_movement_comment(remarks)
    except rules.FTSValidationError as exc:
        if exc.code == "admin_operational_forbidden":
            raise PermissionDeniedError(exc.args[0], code=exc.code) from exc
        raise BadRequestError(exc.args[0], code=exc.code) from exc

    with transaction.atomic():
        qs = FTSFile.objects.select_for_update()
        if str(file_id_or_pk).isdigit():
            file_obj = qs.filter(id=int(file_id_or_pk)).first()
        else:
            file_obj = qs.filter(file_id=file_id_or_pk).first()

        if not file_obj:
            raise NotFoundError("The requested file was not found.")

        if file_obj.status != state_machine.CIRCULATING:
            msg = f"Cannot return file in '{file_obj.status}' state. Only circulating files return."
            raise ConflictError(msg, code="invalid_state_for_return")

        if file_obj.current_holder_id != sender_id:
            raise PermissionDeniedError(
                "You are not the current holder of this file and cannot return it.",
                code="not_current_holder",
            )

        last_movement = file_obj.movements.order_by("-sequence_number").first()
        if not last_movement:
            raise ConflictError(
                "Cannot return a file that has no recorded movement history.",
                code="no_previous_sender",
            )

        target_receiver_id = last_movement.sender_id
        target_receiver_designation = last_movement.sender_designation

        try:
            rules.validate_return_recipient(
                current_holder_id=sender_id,
                target_receiver_id=target_receiver_id,
                expected_previous_sender_id=target_receiver_id,
            )
        except rules.FTSValidationError as exc:
            raise BadRequestError(exc.args[0], code=exc.code) from exc

        new_seq = last_movement.sequence_number + 1

        mov = FileMovement.objects.create(
            file=file_obj,
            sequence_number=new_seq,
            sender_id=sender_id,
            sender_designation=sender_designation,
            receiver_id=target_receiver_id,
            receiver_designation=target_receiver_designation,
            action="returned",
            remarks=remarks.strip(),
        )

        FileComment.objects.create(
            file=file_obj,
            movement=mov,
            author_id=sender_id,
            author_designation=sender_designation,
            comment_text=remarks.strip(),
        )

        if attachments:
            for att in attachments:
                FileAttachment.objects.create(
                    file=file_obj,
                    movement=mov,
                    uploader_id=sender_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", "application/octet-stream"),
                )

        file_obj.current_holder_id = target_receiver_id
        file_obj.current_holder_designation = target_receiver_designation
        file_obj.save(update_fields=[
            "current_holder_id",
            "current_holder_designation",
            "updated_at",
        ])

        FTSAuditLog.objects.create(
            file=file_obj,
            actor_id=sender_id,
            actor_role=sender_designation,
            action_type="return_file",
            details={
                "file_id": file_obj.file_id,
                "sequence": new_seq,
                "receiver_id": target_receiver_id,
            },
        )
        return mov


def archive_file(
    *,
    file_id_or_pk: str,
    actor_id: int,
    actor_designation: str = "",
    remarks: str = "",
    is_employee: bool = True,
    is_system_admin: bool = False,
) -> FTSFile:
    """Archive a completed circulating file (BW-FTS-04, CFR-FTS-008, BR-FTS-012)."""
    try:
        rules.validate_operational_role(is_employee, is_system_admin)
    except rules.FTSValidationError as exc:
        if exc.code == "admin_operational_forbidden":
            raise PermissionDeniedError(exc.args[0], code=exc.code) from exc
        raise BadRequestError(exc.args[0], code=exc.code) from exc

    with transaction.atomic():
        qs = FTSFile.objects.select_for_update()
        if str(file_id_or_pk).isdigit():
            file_obj = qs.filter(id=int(file_id_or_pk)).first()
        else:
            file_obj = qs.filter(file_id=file_id_or_pk).first()

        if not file_obj:
            raise NotFoundError("The requested file was not found.")

        try:
            rules.validate_owner_archival(
                owner_id=file_obj.owner_id,
                actor_id=actor_id,
                current_status=file_obj.status,
            )
        except rules.FTSValidationError as exc:
            if exc.code == "owner_archival_only":
                raise PermissionDeniedError(exc.args[0], code=exc.code) from exc
            raise ConflictError(exc.args[0], code=exc.code) from exc

        file_obj.status = state_machine.ARCHIVED
        file_obj.save(update_fields=["status", "updated_at"])

        last_seq = (
            file_obj.movements.order_by("-sequence_number")
            .values_list("sequence_number", flat=True)
            .first()
            or 0
        )
        new_seq = last_seq + 1

        mov = FileMovement.objects.create(
            file=file_obj,
            sequence_number=new_seq,
            sender_id=actor_id,
            sender_designation=actor_designation,
            receiver_id=actor_id,
            receiver_designation=actor_designation,
            action="archived",
            remarks=remarks.strip() if remarks else "File archived by owner.",
        )

        if remarks and remarks.strip():
            FileComment.objects.create(
                file=file_obj,
                movement=mov,
                author_id=actor_id,
                author_designation=actor_designation,
                comment_text=remarks.strip(),
            )

        FTSAuditLog.objects.create(
            file=file_obj,
            actor_id=actor_id,
            actor_role=actor_designation,
            action_type="archive_file",
            details={"file_id": file_obj.file_id, "status": "archived"},
        )
        return file_obj
