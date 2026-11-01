"""iwd's public surface. The ONLY thing other modules may import.

Plural by signature on purpose (ADR-0013, ops/checks/contracts_are_plural.py).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ComplaintDTO:
    complaint_id: int
    complainant_id: int
    status: str
    issue_category: str
    location: str


def get_complaints(complaint_ids: Sequence[int]) -> dict[int, ComplaintDTO]:
    """Batched complaint retrieval for cross-module integration."""
    ids = {int(i) for i in complaint_ids if i is not None}
    if not ids:
        return {}
    from modules.iwd.models import Complaint

    qs = Complaint.objects.filter(pk__in=ids)
    return {
        c.pk: ComplaintDTO(
            complaint_id=c.pk,
            complainant_id=c.user_id,
            status=c.status,
            issue_category=c.category,
            location=c.location,
        )
        for c in qs
    }
