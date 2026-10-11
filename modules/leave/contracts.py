"""leave's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: all getters accept a sequence of IDs.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LeaveSummaryDTO:
    user_id: int
    cl_available: Decimal = Decimal("0.0")
    rh_available: Decimal = Decimal("0.0")
    scl_available: Decimal = Decimal("0.0")
    el_available: Decimal = Decimal("0.0")
    col_available: Decimal = Decimal("0.0")
    vl_available: Decimal = Decimal("0.0")


def get_leave_summaries(user_ids: Sequence[int]) -> dict[int, LeaveSummaryDTO]:
    """Batched lookup of leave balance summaries."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    return {uid: LeaveSummaryDTO(user_id=uid) for uid in ids}
