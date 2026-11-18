"""Cross-module contracts for Visitor Hostel Management.

All cross-module getters must be plural (taking a Sequence of user_ids).
"""
from collections.abc import Sequence

from .models import Booking


def get_booking_counts(user_ids: Sequence[int]) -> dict[int, dict]:
    """Return total and active booking counts for a sequence of user IDs."""
    result = {uid: {"total": 0, "active": 0} for uid in user_ids}
    bookings = Booking.objects.filter(indenter_id__in=user_ids)
    for b in bookings:
        result[b.indenter_id]["total"] += 1
        if b.status in ("approved", "checked_in"):
            result[b.indenter_id]["active"] += 1
    return result


def get_active_stays(user_ids: Sequence[int]) -> dict[int, list]:
    """Return current active stay details for a sequence of user IDs."""
    result = {uid: [] for uid in user_ids}
    bookings = Booking.objects.filter(indenter_id__in=user_ids, status="checked_in")
    for b in bookings:
        result[b.indenter_id].append({
            "booking_id": b.id,
            "visitor_name": b.visitor_name,
            "check_in_date": str(b.check_in_date),
            "check_out_date": str(b.check_out_date),
        })
    return result
