"""RSPC public contracts surface.

All signatures are strictly plural to avoid N+1 query patterns across modules.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.rspc.models import Project


@dataclass(frozen=True)
class FacultyProjectSummaryDTO:
    user_id: int
    active_project_count: int
    total_sanctioned_amount: Decimal


def get_faculty_project_summaries(user_ids: Sequence[int]) -> dict[int, FacultyProjectSummaryDTO]:
    """Return active project count and total funding volume for a sequence of faculty user IDs."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}

    summaries = {}
    for uid in ids:
        user_projects = Project.objects.filter(user_id=uid, status="active")
        count = user_projects.count()
        total = sum((p.sanctioned_amount for p in user_projects), Decimal("0.00"))
        summaries[uid] = FacultyProjectSummaryDTO(
            user_id=uid,
            active_project_count=count,
            total_sanctioned_amount=total,
        )
    return summaries
