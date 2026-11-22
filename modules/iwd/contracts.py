"""iwd's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional
from modules.iwd.models import Complaint, Estimate


@dataclass(frozen=True)
class ComplaintSummaryDTO:
    id: int
    title: str
    category: str
    status: str
    urgency: str
    requester_id: str


def get_complaint_summaries(
    complaint_ids: Sequence[int]
) -> dict[int, ComplaintSummaryDTO]:
    ids = {int(i) for i in complaint_ids if i is not None}
    if not ids:
        return {}
    rows = Complaint.objects.filter(id__in=ids)
    return {
        c.id: ComplaintSummaryDTO(
            id=c.id,
            title=c.title,
            category=c.category,
            status=c.status,
            urgency=c.urgency,
            requester_id=c.requester_id,
        )
        for c in rows
    }


def get_complaint_estimates(
    complaint_ids: Sequence[int]
) -> dict[int, Optional[float]]:
    ids = {int(i) for i in complaint_ids if i is not None}
    if not ids:
        return {}
    rows = Estimate.objects.filter(complaint_id__in=ids)
    res = {cid: None for cid in ids}
    for e in rows:
        res[e.complaint_id] = float(e.total_cost)
    return res
