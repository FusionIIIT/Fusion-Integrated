"""The ONLY importable surface for other modules."""
from __future__ import annotations

from typing import Sequence

from modules.courses.models import CourseWorkspace


def get_workspace_summaries(workspace_ids: Sequence[int]) -> dict[int, dict]:
    """Workspace summary dictionary keyed by workspace id."""
    rows = CourseWorkspace.objects.filter(id__in=workspace_ids).values(
        "id", "code", "title", "semester", "academic_year", "is_published",
    )
    return {r["id"]: r for r in rows}
