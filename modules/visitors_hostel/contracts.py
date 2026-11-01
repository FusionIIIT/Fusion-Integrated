"""Public cross-module contract for Visitors Hostel.

Other modules may import this file only. Identifiers crossing the module
boundary are IAM user ids; this module owns every table it writes.
"""

from collections.abc import Sequence


def get_booking_summaries(booking_ids: Sequence[int]) -> dict[int, dict]:
    """Return summaries keyed by booking id for approved integrations.

    Kept deliberately plural to avoid cross-module N+1 queries.
    """
    from modules.visitors_hostel.models import Booking

    rows = Booking.objects.filter(pk__in=booking_ids).values(
        "id", "booking_number", "status", "arrival_date", "departure_date")
    return {row["id"]: row for row in rows}
