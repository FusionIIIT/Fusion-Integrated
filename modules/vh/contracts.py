"""VH module cross-boundary contracts.

Per ops/checks/contracts_are_plural.py, cross-module getters must accept
a sequence of IDs rather than singular IDs to prevent N+1 queries.
"""
from collections.abc import Sequence

from .models import Bill, Booking, Room


def get_bookings_for_users(user_ids: Sequence[int]) -> list[dict]:
    """Retrieve summarized bookings for given user/indenter IDs."""
    qs = Booking.objects.filter(indenter_id__in=user_ids)
    return [
        {
            "id": b.id,
            "booking_reference": b.booking_reference,
            "indenter_id": b.indenter_id,
            "visitor_name": b.visitor_name,
            "status": b.status,
            "check_in_date": str(b.check_in_date),
            "check_out_date": str(b.check_out_date),
        }
        for b in qs
    ]


def get_rooms_by_ids(room_ids: Sequence[int]) -> list[dict]:
    """Retrieve summarized room information for given room IDs."""
    qs = Room.objects.filter(id__in=room_ids)
    return [
        {
            "id": r.id,
            "room_number": r.room_number,
            "room_type": r.room_type,
            "occupancy_type": r.occupancy_type,
            "status": r.status,
        }
        for r in qs
    ]


def get_bills_for_bookings(booking_ids: Sequence[int]) -> list[dict]:
    """Retrieve finalized bill amounts for given booking IDs."""
    qs = Bill.objects.filter(booking_id__in=booking_ids)
    return [
        {
            "id": bill.id,
            "booking_id": bill.booking_id,
            "total_amount": str(bill.total_amount),
            "is_settled": bill.is_settled,
            "is_finalized": bill.is_finalized,
        }
        for bill in qs
    ]
