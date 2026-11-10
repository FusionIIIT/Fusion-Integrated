"""Fusion Clean Architecture - File Tracking System (FTS) Inbox/Outbox Selectors.

Implements FTS-UC-005 (View Inbox, Outbox, and Open Files).
"""

from modules.fts.domain.workflow import (
    STATUS_ARCHIVED,
    STATUS_DRAFT,
)
from modules.fts.models import FTSFile, FTSMovement


def get_user_inbox_files(user_id: str) -> list[dict]:
    """Retrieves all active files currently held by the specified user (Inbox).

    Files in draft or archived state are excluded from the inbox.
    """
    files = (
        FTSFile.objects.filter(
            current_holder_id=user_id,
            is_draft=False,
        )
        .exclude(status__in=[STATUS_DRAFT, STATUS_ARCHIVED])
        .order_by("-updated_at")
    )

    return [
        {
            "id": f.id,
            "uin": f.uin,
            "subject": f.subject,
            "priority": f.priority,
            "category": f.category,
            "status": f.status,
            "creator_id": f.creator_id,
            "current_holder_id": f.current_holder_id,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }
        for f in files
    ]


def get_user_outbox_files(user_id: str) -> list[dict]:
    """Retrieves active files that the user forwarded or returned to someone else (Outbox).

    Excludes files currently held by the user or files in draft state.
    """
    # Find all file IDs where the user was a sender
    sent_file_ids = (
        FTSMovement.objects.filter(from_user_id=user_id)
        .values_list("file_id", flat=True)
        .distinct()
    )

    files = (
        FTSFile.objects.filter(
            id__in=sent_file_ids,
            is_draft=False,
        )
        .exclude(current_holder_id=user_id)
        .exclude(status=STATUS_DRAFT)
        .order_by("-updated_at")
    )

    return [
        {
            "id": f.id,
            "uin": f.uin,
            "subject": f.subject,
            "priority": f.priority,
            "category": f.category,
            "status": f.status,
            "creator_id": f.creator_id,
            "current_holder_id": f.current_holder_id,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }
        for f in files
    ]
