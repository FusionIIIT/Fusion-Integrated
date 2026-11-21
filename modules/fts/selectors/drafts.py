"""Fusion Clean Architecture - File Tracking System (FTS) Draft Selectors.

Encapsulates read queries for draft files owned by specific employees.
"""

from modules.fts.domain.workflow import STATUS_DRAFT
from modules.fts.models import FTSFile


def get_user_draft_files(creator_id: str) -> list[dict]:
    """Retrieves all draft files created by a specific user.

    :param creator_id: Employee ID of the creator.
    :return: List of draft file data dictionaries.
    """
    drafts = FTSFile.objects.filter(
        creator_id=creator_id,
        is_draft=True,
        status=STATUS_DRAFT,
    ).order_by("-updated_at")

    return [
        {
            "id": f.id,
            "uin": f.uin,
            "subject": f.subject,
            "description": f.description,
            "priority": f.priority,
            "category": f.category,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }
        for f in drafts
    ]


def get_draft_by_id(file_id: int, creator_id: str) -> dict | None:
    """Retrieves a single draft file by ID, enforcing creator ownership.

    :param file_id: Primary key of the file.
    :param creator_id: Employee ID of the creator.
    :return: File data dictionary or None if not found or unauthorized.
    """
    try:
        f = FTSFile.objects.get(
            id=file_id,
            creator_id=creator_id,
            is_draft=True,
            status=STATUS_DRAFT,
        )
        return {
            "id": f.id,
            "uin": f.uin,
            "subject": f.subject,
            "description": f.description,
            "priority": f.priority,
            "category": f.category,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }
    except FTSFile.DoesNotExist:
        return None
