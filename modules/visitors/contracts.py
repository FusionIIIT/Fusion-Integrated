"""visitors' public surface. Plural by signature.

Ref: 01_VMS_Problem_Statement_v1.2 (boundary B-01 … B-05)
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from modules.visitors.models import VisitRequest


@dataclass(frozen=True)
class VisitorPresenceDTO:
    user_id: int
    visit_id: int
    visitor_name: str
    status: str
    expected_date: date


def get_on_site_visitors_for_host(host_user_ids: Sequence[int]
                                  ) -> dict[int, list[VisitorPresenceDTO]]:
    """Which visitors are currently on site for the given hosts."""
    ids = {int(i) for i in host_user_ids if i is not None}
    if not ids:
        return {}
    out: dict[int, list[VisitorPresenceDTO]] = {uid: [] for uid in ids}
    for row in (VisitRequest.objects
                .filter(host_user_id__in=ids, status="on_site")):
        out[row.host_user_id].append(VisitorPresenceDTO(
            user_id=row.host_user_id,
            visit_id=row.pk,
            visitor_name=row.visitor_name,
            status=row.status,
            expected_date=row.expected_date,
        ))
    return out


def get_visit_count_by_date(from_date: date, to_date: date) -> int:
    """Total visits in a date range — for cross-module analytics."""
    return (VisitRequest.objects
            .filter(expected_date__gte=from_date, expected_date__lte=to_date)
            .exclude(status__in=("draft", "cancelled", "expired"))
            .count())
