"""Querysets scoped by user association and permissions (BR-FTS-009, AFR-FTS-029..034).

All reads pass through here. Ownership/association filtering narrows the
queryset so an unauthorized file returns 404 rather than disclosing its existence.
"""

from django.db.models import Q, QuerySet

from modules.filetracking.models import FileAuditLog, FileMovement, TrackedFile


def associated_files_filter(user_id: int) -> Q:
    """Q filter for files associated with user_id (BR-FTS-009)."""
    return (
        Q(creator_user_id=user_id)
        | Q(owner_user_id=user_id)
        | Q(current_holder_user_id=user_id)
        | Q(movements__sender_user_id=user_id)
        | Q(movements__receiver_user_id=user_id)
        | Q(comments__author_user_id=user_id)
    )


def visible_files(user_id: int) -> QuerySet[TrackedFile]:
    """All files associated with the user across draft, circulated, and archived states."""
    # Pre-circulation drafts are only visible to their creator
    drafts_q = Q(status="draft", creator_user_id=user_id)
    circulated_or_archived_q = (
        Q(status__in=["circulated", "archived"]) & associated_files_filter(user_id)
    )

    return (
        TrackedFile.objects.filter(drafts_q | circulated_or_archived_q)
        .prefetch_related("movements", "comments", "attachments")
        .distinct()
    )


def get_visible_file(user_id: int, file_id: int) -> TrackedFile | None:
    """Get a single file if visible/associated with user, else None (results in 404)."""
    return visible_files(user_id).filter(pk=file_id).first()


def visible_inbox(user_id: int) -> QuerySet[TrackedFile]:
    """AFR-FTS-029, AFR-FTS-031: Files received by user currently awaiting action."""
    return (
        TrackedFile.objects.filter(
            current_holder_user_id=user_id,
            status="circulated",
        )
        .prefetch_related("movements", "comments", "attachments")
        .order_by("-updated_at")
    )


def visible_outbox(user_id: int) -> QuerySet[TrackedFile]:
    """AFR-FTS-030, AFR-FTS-032: Files sent / forwarded by the user in circulation."""
    return (
        TrackedFile.objects.filter(
            status="circulated",
            movements__sender_user_id=user_id,
        )
        .exclude(current_holder_user_id=user_id)  # currently held files are in Inbox
        .prefetch_related("movements", "comments", "attachments")
        .distinct()
        .order_by("-updated_at")
    )


def visible_drafts(user_id: int) -> QuerySet[TrackedFile]:
    """AFR-FTS-014..016: Pre-circulation draft files created by the user."""
    return (
        TrackedFile.objects.filter(
            creator_user_id=user_id,
            status="draft",
        )
        .prefetch_related("comments", "attachments")
        .order_by("-updated_at")
    )


def visible_archived(user_id: int) -> QuerySet[TrackedFile]:
    """AFR-FTS-045: Archived files associated with the user."""
    return (
        TrackedFile.objects.filter(
            status="archived",
        )
        .filter(associated_files_filter(user_id))
        .prefetch_related("movements", "comments", "attachments")
        .distinct()
        .order_by("-archived_at")
    )


def get_file_tracking_history(user_id: int, file_id: int) -> QuerySet[FileMovement]:
    """AFR-FTS-035..041: Chronological movement history for an associated file."""
    file_obj = get_visible_file(user_id, file_id)
    if not file_obj:
        return FileMovement.objects.none()
    return (
        FileMovement.objects.filter(file=file_obj)
        .prefetch_related("comments", "attachments")
        .order_by("created_at")
    )


def visible_audit_logs(
    actor_user_id: int | None = None,
    file_id: int | None = None,
    action: str | None = None,
) -> QuerySet[FileAuditLog]:
    """AFR-FTS-007, AFR-FTS-008, AFR-FTS-054..059: System Admin governance audit logs."""
    qs = FileAuditLog.objects.all().order_by("-created_at")
    if actor_user_id:
        qs = qs.filter(actor_user_id=actor_user_id)
    if file_id:
        qs = qs.filter(file_id=file_id)
    if action:
        qs = qs.filter(action=action)
    return qs
