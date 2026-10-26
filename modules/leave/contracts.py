"""leave's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: all getters accept a sequence of IDs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from modules.leave.models import LeaveBalance


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
    """Batched lookup of leave balance summaries for requested users in the current leave year."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    current_year = timezone.now().year
    rows = LeaveBalance.objects.filter(user_id__in=ids, year=current_year).values_list(
        "user_id", "leave_type__code", "available_days"
    )

    user_balances: dict[int, dict[str, Decimal]] = {uid: {} for uid in ids}
    for uid, code, avail in rows:
        if uid in user_balances and code:
            user_balances[uid][code.upper()] = avail

    results: dict[int, LeaveSummaryDTO] = {}
    for uid in ids:
        b = user_balances[uid]
        results[uid] = LeaveSummaryDTO(
            user_id=uid,
            cl_available=b.get("CL", Decimal("0.0")),
            rh_available=b.get("RH", Decimal("0.0")),
            scl_available=b.get("SCL", Decimal("0.0")),
            el_available=b.get("EL", Decimal("0.0")),
            col_available=b.get("COL", Decimal("0.0")),
            vl_available=b.get("VL", Decimal("0.0")),
        )
    return results
