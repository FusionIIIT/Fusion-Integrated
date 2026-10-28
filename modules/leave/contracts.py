"""leave's public surface. The ONLY thing other modules may import.

Plural by signature on purpose — a singular get_x(id) is what gets called
inside a loop. `ops/checks/contracts_are_plural.py` enforces the shape.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.leave.models import LeaveApplication


@dataclass(frozen=True)
class LeaveSummaryDTO:
    user_id: int
    active_days: int
    pending_requests: int


def get_leave_summaries(user_ids: Sequence[int]) -> dict[int, LeaveSummaryDTO]:
    """Whether each employee is on sanctioned leave or has a pending request.

    Batched over a sequence of ids so a caller rendering a list cannot drift
    into an N+1.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    from django.db.models import Count, Q

    rows = (LeaveApplication.objects.filter(applicant_user_id__in=ids)
            .values("applicant_user_id")
            .annotate(
                active_days=Count("pk", filter=Q(status="sanctioned")),
                pending_requests=Count("pk", filter=Q(status="pending")),
            ))
    return {
        r["applicant_user_id"]: LeaveSummaryDTO(
            user_id=r["applicant_user_id"],
            active_days=r["active_days"],
            pending_requests=r["pending_requests"],
        )
        for r in rows
    }
