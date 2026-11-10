"""vms's public surface for other modules. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class VisitStatusDTO:
    user_id: int
    pending_requests: int
    visitors_on_site: int


def get_visit_status(user_ids: Sequence[int]) -> dict[int, VisitStatusDTO]:
    """Stub: per-host visit counts for future modules. Returns nothing until a
    consumer exists (build_sequence/13 section C)."""
    return {}
