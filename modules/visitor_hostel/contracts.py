"""visitor_hostel's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.visitor_hostel.models import Bill, BookingRequest


@dataclass(frozen=True)
class BookingSummaryDTO:
    booking_id: int
    indenter_id: int | None
    status: str
    visitor_name: str
    visitor_category: str
    check_in_date: date
    check_out_date: date
    number_of_rooms: int


def get_booking_summaries(booking_ids: Sequence[int]) -> dict[int, BookingSummaryDTO]:
    """Plural getter for external modules to check hostel booking summaries."""
    ids = {int(i) for i in booking_ids if i is not None}
    if not ids:
        return {}
    qs = BookingRequest.objects.filter(pk__in=ids)
    return {
        b.pk: BookingSummaryDTO(
            booking_id=b.pk,
            indenter_id=b.indenter_id,
            status=b.status,
            visitor_name=b.visitor_name,
            visitor_category=b.visitor_category,
            check_in_date=b.check_in_date,
            check_out_date=b.check_out_date,
            number_of_rooms=b.number_of_rooms,
        )
        for b in qs
    }


@dataclass(frozen=True)
class HostelNoDuesClearanceDTO:
    user_id: int
    cleared: bool
    unsettled_bills_count: int
    outstanding_amount: Decimal
    message: str


def get_hostel_no_dues_clearances(user_ids: Sequence[int]) -> dict[int, HostelNoDuesClearanceDTO]:
    """Plural clearance check for academic/administrative no-dues procedures."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    unsettled = Bill.objects.filter(
        booking__indenter_id__in=ids, is_settled_offline=False
    ).select_related("booking")

    unsettled_by_user: dict[int, list[Bill]] = {uid: [] for uid in ids}
    for b in unsettled:
        if b.booking and b.booking.indenter_id in unsettled_by_user:
            unsettled_by_user[b.booking.indenter_id].append(b)

    results = {}
    for uid in ids:
        bills = unsettled_by_user.get(uid, [])
        if not bills:
            results[uid] = HostelNoDuesClearanceDTO(
                user_id=uid,
                cleared=True,
                unsettled_bills_count=0,
                outstanding_amount=Decimal("0.00"),
                message="No outstanding hostel dues",
            )
        else:
            total = sum((b.total_amount for b in bills), Decimal("0.00"))
            results[uid] = HostelNoDuesClearanceDTO(
                user_id=uid,
                cleared=False,
                unsettled_bills_count=len(bills),
                outstanding_amount=total,
                message=f"Outstanding dues: {len(bills)} unpaid hostel bill(s) totaling INR {total}",
            )
    return results

