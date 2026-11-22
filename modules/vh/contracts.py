# Public contract interface for vh module. Plural signatures only.
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ActiveStayDTO:
    booking_id: int
    booking_reference: str
    visitor_name: str
    visitor_category: str
    room_numbers: list[str]
    arrival_date: date
    departure_date: date
    checkin_time: datetime | None
    checkout_time: datetime | None
    status: str


@dataclass(frozen=True)
class BookingBillingSummaryDTO:
    booking_id: int
    bill_number: str | None
    total_amount: float
    billing_responsibility: str
    is_settled: bool


def get_active_stays(booking_ids: Sequence[int]) -> dict[int, ActiveStayDTO]:
    # Returns active stay records for the requested booking IDs.
    from modules.vh.models.booking import Booking

    ids = {int(bid) for bid in booking_ids if bid is not None}
    if not ids:
        return {}
    bookings = Booking.objects.filter(id__in=ids).prefetch_related("visitors", "allotments__room")
    result: dict[int, ActiveStayDTO] = {}
    for b in bookings:
        first_visitor = b.visitors.first()
        vis_name = first_visitor.name if first_visitor else "Unknown"
        rooms = [a.room.room_number for a in b.allotments.all() if a.room]
        result[b.id] = ActiveStayDTO(
            booking_id=b.id,
            booking_reference=b.booking_reference,
            visitor_name=vis_name,
            visitor_category=b.visitor_category,
            room_numbers=rooms,
            arrival_date=b.arrival_date,
            departure_date=b.departure_date,
            checkin_time=b.checkin_time,
            checkout_time=b.checkout_time,
            status=b.status,
        )
    return result


def get_billing_summaries(booking_ids: Sequence[int]) -> dict[int, BookingBillingSummaryDTO]:
    # Returns billing summaries for the requested booking IDs.
    from modules.vh.models.bill import Bill

    ids = {int(bid) for bid in booking_ids if bid is not None}
    if not ids:
        return {}
    bills = Bill.objects.filter(booking_id__in=ids).select_related("booking")
    result: dict[int, BookingBillingSummaryDTO] = {}
    for bill in bills:
        result[bill.booking_id] = BookingBillingSummaryDTO(
            booking_id=bill.booking_id,
            bill_number=bill.bill_number,
            total_amount=float(bill.total_amount),
            billing_responsibility=bill.billing_responsibility,
            is_settled=(bill.status == "settled"),
        )
    return result
