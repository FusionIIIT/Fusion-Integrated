"""Public contracts and DTOs exposed by the IWD module to the rest of the platform."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.iwd.models import Complaint


@dataclass(frozen=True)
class ComplaintSummaryDTO:
    """Read-only data transfer object for cross-module complaint queries."""

    complaint_id: int
    requester_user_id: int
    category: str
    status: str
    is_resolved: bool


def get_user_complaints_summary(user_ids: Sequence[int]) -> dict[int, list[ComplaintSummaryDTO]]:
    """Return active maintenance complaints summary grouped by user ID."""
    clean_ids = {int(uid) for uid in user_ids if uid is not None}
    if not clean_ids:
        return {}
    complaints = Complaint.objects.filter(requester_user_id__in=clean_ids)
    results: dict[int, list[ComplaintSummaryDTO]] = {uid: [] for uid in clean_ids}
    for c in complaints:
        dto = ComplaintSummaryDTO(
            complaint_id=c.id,
            requester_user_id=c.requester_user_id,
            category=c.category,
            status=c.status,
            is_resolved=c.is_resolved,
        )
        results[c.requester_user_id].append(dto)
    return results
