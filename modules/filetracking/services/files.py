"""File tracking operational services (writes and business workflows).

Every state mutation passes through here inside a transaction.
Enforces BR-FTS-001 through BR-FTS-014 and implements FTS-UC-001..007, FTS-UC-010.
"""
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.filetracking.domain import (
    FileLifecycleState,
    InvalidReturnTargetError,
    UnauthorizedFileActionError,
    assert_can_archive,
    assert_can_discard_draft,
    assert_can_edit_draft,
    assert_can_forward_or_return,
    assert_current_holder,
    assert_operational_actor,
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
    validate_return_recipient,
)
from modules.filetracking.models import (
    FileAttachment,
    FileAuditLog,
    FileComment,
    FileMovement,
    TrackedFile,
)
from modules.filetracking.services.notifications import trigger_fts_notification

P_CREATE = "filetracking.file.create"
P_FORWARD = "filetracking.file.forward"
P_RETURN = "filetracking.file.return"
P_ARCHIVE = "filetracking.file.archive"
P_VIEW = "filetracking.file.view"
P_GOV_VIEW = "filetracking.governance.view"
P_GOV_MANAGE = "filetracking.governance.manage"
P_API_INTEGRATE = "filetracking.api.integrate"


def create_draft(
    subject: str,
    description: str,
    creator_user_id: int,
    creator_role: str,
    initial_comment: str,
    attachments_data: list[dict[str, Any]] | None = None,
    source_module: str = "filetracking",
    external_reference: str = "",
    is_system_admin: bool = False,
    ip_address: str | None = None,
) -> TrackedFile:
    """FTS-UC-001 / CFR-FTS-003: Create a new file in DRAFT state.

    Enforces BR-FTS-001 (operational access), BR-FTS-004 (mandatory initial comment).
    """
    assert_operational_actor(is_system_admin)
    clean_comment = validate_initial_comment(initial_comment)

    with transaction.atomic():
        tracked_file = TrackedFile.objects.create(
            subject=subject.strip(),
            description=description.strip(),
            status="draft",
            creator_user_id=creator_user_id,
            creator_role=creator_role,
            owner_user_id=creator_user_id,
            current_holder_user_id=creator_user_id,
            current_holder_role=creator_role,
            source_module=source_module,
            external_reference=external_reference,
        )

        FileComment.objects.create(
            file=tracked_file,
            author_user_id=creator_user_id,
            author_role=creator_role,
            comment_text=clean_comment,
        )

        if attachments_data:
            for att in attachments_data:
                FileAttachment.objects.create(
                    file=tracked_file,
                    uploaded_by_user_id=creator_user_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", ""),
                )

        FileAuditLog.objects.create(
            file=tracked_file,
            action="file.created",
            actor_user_id=creator_user_id,
            actor_role=creator_role,
            ip_address=ip_address,
            details={
                "subject": tracked_file.subject,
                "file_code": tracked_file.file_code,
                "status": "draft",
            },
        )

    return tracked_file


def edit_draft(
    file_id: int,
    actor_user_id: int,
    actor_role: str,
    subject: str | None = None,
    description: str | None = None,
    new_comment: str | None = None,
    new_attachments: list[dict[str, Any]] | None = None,
    is_system_admin: bool = False,
    ip_address: str | None = None,
) -> TrackedFile:
    """FTS-UC-002: Edit a saved pre-circulation draft (BR-FTS-005)."""
    assert_operational_actor(is_system_admin)

    with transaction.atomic():
        tracked_file = TrackedFile.objects.select_for_update().get(pk=file_id)

        assert_can_edit_draft(FileLifecycleState(tracked_file.status))
        if tracked_file.creator_user_id != actor_user_id:
            raise UnauthorizedFileActionError("Only the draft creator may edit this draft.")

        if subject is not None and subject.strip():
            tracked_file.subject = subject.strip()
        if description is not None:
            tracked_file.description = description.strip()
        tracked_file.save()

        if new_comment and new_comment.strip():
            first_comment = tracked_file.comments.order_by("created_at").first()
            if first_comment:
                first_comment.comment_text = new_comment.strip()
                first_comment.save()
            else:
                FileComment.objects.create(
                    file=tracked_file,
                    author_user_id=actor_user_id,
                    author_role=actor_role,
                    comment_text=new_comment.strip(),
                )

        if new_attachments:
            for att in new_attachments:
                FileAttachment.objects.create(
                    file=tracked_file,
                    uploaded_by_user_id=actor_user_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", ""),
                )

        FileAuditLog.objects.create(
            file=tracked_file,
            action="file.draft_edited",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            ip_address=ip_address,
            details={"file_code": tracked_file.file_code},
        )

    return tracked_file


def discard_draft(
    file_id: int,
    actor_user_id: int,
    actor_role: str,
    is_system_admin: bool = False,
    ip_address: str | None = None,
) -> None:
    """FTS-UC-002: Discard draft before submission (BR-FTS-005, AFR-FTS-016).

    Circulated files cannot be deleted/discarded (BR-FTS-005, AFR-FTS-017).
    """
    assert_operational_actor(is_system_admin)

    with transaction.atomic():
        tracked_file = TrackedFile.objects.select_for_update().get(pk=file_id)

        assert_can_discard_draft(FileLifecycleState(tracked_file.status))
        if tracked_file.creator_user_id != actor_user_id:
            raise UnauthorizedFileActionError("Only the draft creator may discard this draft.")

        FileAuditLog.objects.create(
            file=None,
            action="file.draft_discarded",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            ip_address=ip_address,
            details={
                "file_id": tracked_file.id,
                "file_code": tracked_file.file_code,
                "subject": tracked_file.subject,
            },
        )

        tracked_file.delete()


def forward_file(
    file_id: int,
    sender_user_id: int,
    sender_role: str,
    receiver_user_id: int,
    receiver_role: str,
    comment: str,
    attachments_data: list[dict[str, Any]] | None = None,
    is_system_admin: bool = False,
    ip_address: str | None = None,
) -> FileMovement:
    """FTS-UC-003 / CFR-FTS-005: Forward active file to another employee.

    Initial circulation or onward forwarding.
    Enforces BR-FTS-001, BR-FTS-006 (mandatory movement comment),
    BR-FTS-007 (valid recipient), BR-FTS-008 (chronological record).
    """
    assert_operational_actor(is_system_admin)
    clean_comment = validate_movement_comment(comment)
    validate_forward_recipient(receiver_user_id, sender_user_id)

    with transaction.atomic():
        tracked_file = TrackedFile.objects.select_for_update().get(pk=file_id)

        assert_can_forward_or_return(FileLifecycleState(tracked_file.status))
        assert_current_holder(sender_user_id, tracked_file.current_holder_user_id)

        # Transition draft to circulated if first send
        is_first_circulation = tracked_file.status == "draft"
        if is_first_circulation:
            tracked_file.status = "circulated"

        tracked_file.current_holder_user_id = receiver_user_id
        tracked_file.current_holder_role = receiver_role
        tracked_file.save()

        movement = FileMovement.objects.create(
            file=tracked_file,
            movement_type="forward",
            sender_user_id=sender_user_id,
            sender_role=sender_role,
            receiver_user_id=receiver_user_id,
            receiver_role=receiver_role,
            comment=clean_comment,
        )

        FileComment.objects.create(
            file=tracked_file,
            movement=movement,
            author_user_id=sender_user_id,
            author_role=sender_role,
            comment_text=clean_comment,
        )

        if attachments_data:
            for att in attachments_data:
                FileAttachment.objects.create(
                    file=tracked_file,
                    movement=movement,
                    uploaded_by_user_id=sender_user_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", ""),
                )

        FileAuditLog.objects.create(
            file=tracked_file,
            action="file.forwarded",
            actor_user_id=sender_user_id,
            actor_role=sender_role,
            ip_address=ip_address,
            details={
                "movement_id": movement.id,
                "from_user_id": sender_user_id,
                "to_user_id": receiver_user_id,
                "first_circulation": is_first_circulation,
            },
        )

        # Trigger notifications (BR-FTS-013, AFR-FTS-061, AFR-FTS-062)
        trigger_fts_notification(
            event_type="file.received",
            recipient_user_id=receiver_user_id,
            file_id=tracked_file.id,
            subject=f"File Received: {tracked_file.file_code}",
            message=f"File '{tracked_file.subject}' forwarded to you by user {sender_user_id}.",
        )
        trigger_fts_notification(
            event_type="file.forwarded",
            recipient_user_id=sender_user_id,
            file_id=tracked_file.id,
            subject=f"File Forwarded: {tracked_file.file_code}",
            message=f"File '{tracked_file.subject}' forwarded to user {receiver_user_id}.",
        )

    return movement


def return_file(
    file_id: int,
    sender_user_id: int,
    sender_role: str,
    comment: str,
    attachments_data: list[dict[str, Any]] | None = None,
    is_system_admin: bool = False,
    ip_address: str | None = None,
) -> FileMovement:
    """FTS-UC-004 / CFR-FTS-005: Return received file to previous sender.

    Enforces BR-FTS-006, BR-FTS-007 (routes return strictly to previous sender).
    """
    assert_operational_actor(is_system_admin)
    clean_comment = validate_movement_comment(comment)

    with transaction.atomic():
        tracked_file = TrackedFile.objects.select_for_update().get(pk=file_id)

        assert_can_forward_or_return(FileLifecycleState(tracked_file.status))
        assert_current_holder(sender_user_id, tracked_file.current_holder_user_id)

        # Last movement indicates previous sender
        last_movement = (
            FileMovement.objects.filter(file=tracked_file)
            .order_by("-created_at")
            .first()
        )
        if not last_movement:
            raise InvalidReturnTargetError("File has no previous sender to return to (BR-FTS-007).")

        previous_sender_id = last_movement.sender_user_id
        previous_sender_role = last_movement.sender_role
        validate_return_recipient(previous_sender_id, previous_sender_id)

        tracked_file.current_holder_user_id = previous_sender_id
        tracked_file.current_holder_role = previous_sender_role
        tracked_file.save()

        movement = FileMovement.objects.create(
            file=tracked_file,
            movement_type="return",
            sender_user_id=sender_user_id,
            sender_role=sender_role,
            receiver_user_id=previous_sender_id,
            receiver_role=previous_sender_role,
            comment=clean_comment,
        )

        FileComment.objects.create(
            file=tracked_file,
            movement=movement,
            author_user_id=sender_user_id,
            author_role=sender_role,
            comment_text=clean_comment,
        )

        if attachments_data:
            for att in attachments_data:
                FileAttachment.objects.create(
                    file=tracked_file,
                    movement=movement,
                    uploaded_by_user_id=sender_user_id,
                    file_name=att.get("file_name", "attachment"),
                    file_path=att.get("file_path", ""),
                    file_size=att.get("file_size", 0),
                    mime_type=att.get("mime_type", ""),
                )

        FileAuditLog.objects.create(
            file=tracked_file,
            action="file.returned",
            actor_user_id=sender_user_id,
            actor_role=sender_role,
            ip_address=ip_address,
            details={
                "movement_id": movement.id,
                "from_user_id": sender_user_id,
                "to_user_id": previous_sender_id,
            },
        )

        # Trigger notifications (BR-FTS-013, AFR-FTS-063)
        trigger_fts_notification(
            event_type="file.returned",
            recipient_user_id=previous_sender_id,
            file_id=tracked_file.id,
            subject=f"File Returned: {tracked_file.file_code}",
            message=f"File '{tracked_file.subject}' returned to you by user {sender_user_id}.",
        )

    return movement


def archive_file(
    file_id: int,
    actor_user_id: int,
    actor_role: str,
    is_system_admin: bool = False,
    ip_address: str | None = None,
) -> TrackedFile:
    """FTS-UC-007 / CFR-FTS-008: Archive completed circulated file.

    Enforces BR-FTS-012: Only owner can archive completed circulated files.
    """
    assert_operational_actor(is_system_admin)

    with transaction.atomic():
        tracked_file = TrackedFile.objects.select_for_update().get(pk=file_id)

        assert_can_archive(
            FileLifecycleState(tracked_file.status),
            actor_user_id,
            tracked_file.owner_user_id,
        )

        tracked_file.status = "archived"
        tracked_file.archived_at = timezone.now()
        tracked_file.archived_by_user_id = actor_user_id
        tracked_file.save()

        FileMovement.objects.create(
            file=tracked_file,
            movement_type="archival",
            sender_user_id=actor_user_id,
            sender_role=actor_role,
            receiver_user_id=actor_user_id,
            receiver_role=actor_role,
            comment="File workflow marked completed and archived by owner.",
        )

        FileAuditLog.objects.create(
            file=tracked_file,
            action="file.archived",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            ip_address=ip_address,
            details={"file_code": tracked_file.file_code},
        )

        # Trigger notification (BR-FTS-013, AFR-FTS-064)
        trigger_fts_notification(
            event_type="file.archived",
            recipient_user_id=actor_user_id,
            file_id=tracked_file.id,
            subject=f"File Archived: {tracked_file.file_code}",
            message=f"File '{tracked_file.subject}' has been permanently archived.",
        )

    return tracked_file


def log_governance_action(
    action: str,
    actor_user_id: int,
    actor_role: str,
    details: dict[str, Any],
    file_id: int | None = None,
    ip_address: str | None = None,
) -> FileAuditLog:
    """FTS-UC-009 / AFR-FTS-006..008, AFR-FTS-065: Governance audit logging."""
    file_obj = None
    if file_id:
        file_obj = TrackedFile.objects.filter(pk=file_id).first()

    audit_entry = FileAuditLog.objects.create(
        file=file_obj,
        action=action,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        ip_address=ip_address,
        details=details,
    )

    if action == "role.assigned":
        trigger_fts_notification(
            event_type="role.assigned",
            recipient_user_id=details.get("target_user_id", actor_user_id),
            subject="FTS Role Assigned/Reassigned",
            message=f"Role assignment updated: {details.get('role', '')}",
            payload=details,
        )

    return audit_entry
