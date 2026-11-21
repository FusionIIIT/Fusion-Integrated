"""FTS read scoping and visibility filters (CFR-FTS-006, BR-FTS-009)."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.fts.domain import state_machine
from modules.fts.models import (
    FileAttachment,
    FileComment,
    FileMovement,
    FTSAuditLog,
    FTSFile,
)


def visible_inbox_files(user_id: int) -> QuerySet[FTSFile]:
    """Circulating files currently held by user_id (CFR-FTS-006, FTS-UC-005)."""
    return FTSFile.objects.filter(
        status=state_machine.CIRCULATING,
        current_holder_id=user_id,
    ).order_by("-updated_at")


def visible_outbox_files(user_id: int) -> QuerySet[FTSFile]:
    """Files sent or forwarded by user_id that are not currently in user's inbox."""
    sent_file_ids = (
        FileMovement.objects.filter(sender_id=user_id)
        .values_list("file_id", flat=True)
        .distinct()
    )
    return FTSFile.objects.filter(
        id__in=sent_file_ids,
        status__in=[state_machine.CIRCULATING, state_machine.ARCHIVED],
    ).exclude(
        status=state_machine.CIRCULATING,
        current_holder_id=user_id,
    ).order_by("-updated_at")


def visible_draft_files(user_id: int) -> QuerySet[FTSFile]:
    """Draft files created by user_id (CFR-FTS-004, FTS-UC-002)."""
    return FTSFile.objects.filter(
        status=state_machine.DRAFT,
        creator_id=user_id,
    ).order_by("-updated_at")


def get_visible_file(file_identifier: str, user_id: int) -> FTSFile | None:
    """Return file if user is associated with it, else None (BR-FTS-009)."""
    if file_identifier.isdigit():
        file_obj = FTSFile.objects.filter(
            Q(id=int(file_identifier)) | Q(file_id=file_identifier)
        ).first()
    else:
        file_obj = FTSFile.objects.filter(file_id=file_identifier).first()

    if not file_obj:
        return None

    # Check association: creator, owner, current holder, or participant in movements
    is_associated = (
        file_obj.creator_id == user_id
        or file_obj.owner_id == user_id
        or file_obj.current_holder_id == user_id
    )
    if is_associated:
        return file_obj

    is_in_movements = FileMovement.objects.filter(
        file=file_obj,
    ).filter(
        Q(sender_id=user_id) | Q(receiver_id=user_id)
    ).exists()

    if is_in_movements:
        return file_obj

    return None


def get_file_movements(file_obj: FTSFile) -> QuerySet[FileMovement]:
    """Return chronological movements for a file (CFR-FTS-007, BR-FTS-008)."""
    return file_obj.movements.all().order_by("sequence_number")


def get_file_comments(file_obj: FTSFile) -> QuerySet[FileComment]:
    """Return chronological comments for a file."""
    return file_obj.comments.all().order_by("created_at")


def get_file_attachments(file_obj: FTSFile) -> QuerySet[FileAttachment]:
    """Return attachments for a file."""
    return file_obj.attachments.all().order_by("created_at")


def get_system_audit_logs(actor_id: int | None = None) -> QuerySet[FTSAuditLog]:
    """Return governance audit logs for system administrators (AFR-FTS-008)."""
    qs = FTSAuditLog.objects.all().order_by("-timestamp")
    if actor_id:
        qs = qs.filter(actor_id=actor_id)
    return qs
