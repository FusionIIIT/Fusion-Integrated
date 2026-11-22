"""Query selectors for File Tracking System (all reads, no writes)."""

from django.db.models import Q, QuerySet

from modules.filetracking.domain.entities import FileStatus
from modules.filetracking.models import FileAuditLog, FileMovement, TrackedFile


def get_inbox_files(user_id: int) -> QuerySet[TrackedFile]:
    """Return files currently held by user awaiting action (FTS-UC-005)."""
    return (
        TrackedFile.objects.filter(
            status=FileStatus.CIRCULATING,
            current_holder_user_id=user_id,
        )
        .prefetch_related("movements")
        .order_by("-updated_at")
    )


def get_outbox_files(user_id: int) -> QuerySet[TrackedFile]:
    """Return circulating files user sent or created but does not currently hold (FTS-UC-005)."""
    participated_file_ids = FileMovement.objects.filter(
        sender_user_id=user_id
    ).values_list("file_id", flat=True)

    return (
        TrackedFile.objects.filter(
            status=FileStatus.CIRCULATING,
        )
        .filter(Q(created_by_user_id=user_id) | Q(id__in=participated_file_ids))
        .exclude(current_holder_user_id=user_id)
        .distinct()
        .prefetch_related("movements")
        .order_by("-updated_at")
    )


def get_draft_files(user_id: int) -> QuerySet[TrackedFile]:
    """Return uncirculated draft files created by user (FTS-UC-002, FTS-UC-005)."""
    return (
        TrackedFile.objects.filter(
            status=FileStatus.DRAFT,
            created_by_user_id=user_id,
        )
        .prefetch_related("attachments")
        .order_by("-updated_at")
    )


def get_archived_files(user_id: int) -> QuerySet[TrackedFile]:
    """Return completed archived files associated with user (FTS-UC-007, BR-FTS-012)."""
    participated_file_ids = FileMovement.objects.filter(
        Q(sender_user_id=user_id) | Q(receiver_user_id=user_id)
    ).values_list("file_id", flat=True)

    return (
        TrackedFile.objects.filter(
            status=FileStatus.ARCHIVED,
            is_archived=True,
        )
        .filter(Q(created_by_user_id=user_id) | Q(id__in=participated_file_ids))
        .distinct()
        .prefetch_related("movements", "attachments")
        .order_by("-archived_at", "-updated_at")
    )


def get_file_movements(file_id: int) -> QuerySet[FileMovement]:
    """Return chronological movement history for a file (BR-FTS-008, FTS-UC-006)."""
    return FileMovement.objects.filter(file_id=file_id).order_by("sequence_number")


def get_audit_logs(file_id: int | None = None) -> QuerySet[FileAuditLog]:
    """Return audit records (BR-FTS-011, FTS-UC-009)."""
    qs = FileAuditLog.objects.all().order_by("-created_at")
    if file_id is not None:
        qs = qs.filter(file_id=file_id)
    return qs
