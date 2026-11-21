"""Fusion Clean Architecture - File Tracking System (FTS) Movement Selectors.

Encapsulates read queries for file movements and audit trails.
"""

from modules.fts.models import FTSMovement


def get_file_movement_history(file_id: int) -> list[dict]:
    """Retrieves the chronological audit trail of movements for a file (BR-FTS-008).

    :param file_id: Primary key of the file.
    :return: Chronological list of movement steps with comments.
    """
    movements = (
        FTSMovement.objects.filter(file_id=file_id)
        .order_by("created_at")
        .prefetch_related("comments")
    )

    history = []
    for m in movements:
        comments_list = [
            {
                "author_id": c.author_id,
                "author_role": c.author_role,
                "remarks": c.remarks,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in m.comments.all()
        ]
        history.append(
            {
                "movement_id": m.id,
                "action": m.action,
                "from_user_id": m.from_user_id,
                "from_role": m.from_role,
                "to_user_id": m.to_user_id,
                "to_role": m.to_role,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "comments": comments_list,
            }
        )

    return history


def get_previous_senders_for_file(file_id: int) -> list[str]:
    """Retrieves ordered previous senders in movement chain for return eligibility."""
    movements = FTSMovement.objects.filter(file_id=file_id).order_by("created_at")
    senders: list[str] = []
    for m in movements:
        if m.from_user_id and m.from_user_id not in senders:
            senders.append(m.from_user_id)
    return senders
