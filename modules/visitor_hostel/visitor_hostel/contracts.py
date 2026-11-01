"""visitor_hostel's public surface — the only thing other modules may import.
Plural by signature, so it cannot be called inside a loop."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Count, Q

from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import Bill, Booking


@dataclass(frozen=True)
class IndenterSummaryDTO:
    user_id: int
    open_bookings: int
    unsettled_bills: int


def get_indenter_summaries(user_ids: Sequence[int]) -> dict[int, IndenterSummaryDTO]:
    """Open VH bookings and unsettled VH bills raised by each person — what a
    clearance or no-dues check would ask. Every requested id gets an answer."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    open_counts = dict(
        Booking.objects.filter(indenter_user_id__in=ids)
        .exclude(status__in=sm.TERMINAL)
        .values_list("indenter_user_id").annotate(n=Count("id")))
    unsettled = dict(
        Bill.objects.filter(booking__indenter_user_id__in=ids)
        .filter(~Q(status="settled"))
        .values_list("booking__indenter_user_id").annotate(n=Count("id")))
    return {uid: IndenterSummaryDTO(uid, open_counts.get(uid, 0), unsettled.get(uid, 0))
            for uid in ids}
