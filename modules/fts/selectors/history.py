"""Read selectors for file tracking history."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.fts.models.movements import FileMovement


def get_file_history(file_id: int) -> QuerySet[FileMovement]:
    """Retrieves chronological movements for a file with comments and attachments."""
    return (
        FileMovement.objects.filter(file_id=file_id)
        .prefetch_related("comments", "attachments")
        .order_by("sequence")
    )
