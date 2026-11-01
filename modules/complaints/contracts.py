"""Cross-module public contracts for Complaint Management System.

Other modules may import ONLY this file from modules.complaints.
All signatures must be plural by contract (no single-record queries).
Contracts are strictly read-only and never mutate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from django.db.models import Count, Q

from modules.complaints.models import Complaint


@dataclass(frozen=True)
class ComplaintCountsDTO:
    user_id: int
    open_count: int
    resolved_count: int
    closed_count: int


@dataclass(frozen=True)
class ComplaintSummaryDTO:
    complaint_id: str
    category: str
    status: str
    priority: str
    is_escalated: bool


def get_user_complaint_counts(user_ids: Sequence[int]) -> dict[int, ComplaintCountsDTO]:
    """Return complaint summary counts for the requested user IDs.

    Plural query avoiding N+1.
    """
    if not user_ids:
        return {}

    rows = (
        Complaint.objects.filter(complainant_user_id__in=user_ids)
        .values("complainant_user_id")
        .annotate(
            open_count=Count("pk", filter=Q(status__in=["submitted", "in_progress"])),
            resolved_count=Count("pk", filter=Q(status="resolved")),
            closed_count=Count("pk", filter=Q(status="closed")),
        )
    )

    result = {}
    for r in rows:
        uid = r["complainant_user_id"]
        result[uid] = ComplaintCountsDTO(
            user_id=uid,
            open_count=r["open_count"],
            resolved_count=r["resolved_count"],
            closed_count=r["closed_count"],
        )

    # Fill default zero counts for any requested users without records
    for uid in user_ids:
        if uid not in result:
            result[uid] = ComplaintCountsDTO(
                user_id=uid,
                open_count=0,
                resolved_count=0,
                closed_count=0,
            )

    return result


def get_complaint_summaries(complaint_ids: Sequence[str]) -> dict[str, ComplaintSummaryDTO]:
    """Return summary records for a list of complaint IDs."""
    if not complaint_ids:
        return {}

    rows = Complaint.objects.filter(complaint_id__in=complaint_ids)
    return {
        c.complaint_id: ComplaintSummaryDTO(
            complaint_id=c.complaint_id,
            category=c.category,
            status=c.status,
            priority=c.priority,
            is_escalated=c.is_escalated,
        )
        for c in rows
    }

