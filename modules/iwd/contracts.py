from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.iwd.models.complaint import Complaint


@dataclass(frozen=True)
class ComplaintSummaryDTO:
    complaint_id: str
    complainant_user_id: int
    category: str
    status: str
    assigned_engineer_id: int | None


def get_complaints_by_user(
    user_ids: Sequence[int],
) -> dict[int, list[ComplaintSummaryDTO]]:
    """Cross-module plural contract for fetching complaint summaries by user ids."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}

    rows = Complaint.objects.filter(complainant_user_id__in=ids).values(
        "complaint_id", "complainant_user_id", "category", "status", "assigned_engineer_id"
    )

    result: dict[int, list[ComplaintSummaryDTO]] = {uid: [] for uid in ids}
    for row in rows:
        uid = row["complainant_user_id"]
        result[uid].append(
            ComplaintSummaryDTO(
                complaint_id=row["complaint_id"],
                complainant_user_id=uid,
                category=row["category"],
                status=row["status"],
                assigned_engineer_id=row["assigned_engineer_id"],
            )
        )
    return result
