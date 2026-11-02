"""External module contracts for Complaint Management System."""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Dict
from django.db.models import Count, Q

from modules.complaints.models import Complaint


@dataclass(frozen=True)
class ComplaintCountsDTO:
    user_id: int
    open_count: int
    resolved_count: int
    closed_count: int
    rejected_count: int


def get_complaint_counts_by_user(user_ids: Sequence[int]) -> Dict[int, ComplaintCountsDTO]:
    """Retrieve complaint counts for a sequence of user IDs. Plural by signature."""
    rows = (
        Complaint.objects.filter(complainant_user_id__in=user_ids)
        .values("complainant_user_id")
        .annotate(
            open_count=Count("pk", filter=Q(status__in=["submitted", "in_progress"])),
            resolved_count=Count("pk", filter=Q(status="resolved")),
            closed_count=Count("pk", filter=Q(status="closed")),
            rejected_count=Count("pk", filter=Q(status="rejected")),
        )
    )

    result = {}
    found_users = set()
    for r in rows:
        uid = r["complainant_user_id"]
        found_users.add(uid)
        result[uid] = ComplaintCountsDTO(
            user_id=uid,
            open_count=r["open_count"],
            resolved_count=r["resolved_count"],
            closed_count=r["closed_count"],
            rejected_count=r["rejected_count"],
        )

    for uid in user_ids:
        if uid not in found_users:
            result[uid] = ComplaintCountsDTO(
                user_id=uid,
                open_count=0,
                resolved_count=0,
                closed_count=0,
                rejected_count=0,
            )

    return result
