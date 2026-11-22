# Query selectors for VHMS bookings.

from django.db.models import Prefetch, QuerySet

from modules.vh.models.booking import Booking
from modules.vh.models.room import RoomAllotment
from modules.vh.selectors.scoping import get_visible_booking_or_404, scope_bookings


def list_bookings(
    principal,
    status: str | None = None,
    is_offline: bool | None = None,
) -> QuerySet[Booking]:
    # Returns scoped query set of bookings with optional status or source filters.
    qs = scope_bookings(
        Booking.objects.all()
        .prefetch_related(
            "visitors",
            Prefetch("allotments", queryset=RoomAllotment.objects.select_related("room")),
        )
        .order_by("-created_at"),
        principal,
    )
    if status:
        qs = qs.filter(status=status.lower())
    if is_offline is not None:
        qs = qs.filter(is_offline=is_offline)
    return qs


def get_booking_detail(booking_id: int, principal) -> Booking:
    # Returns detailed booking record with related visitors and allotments.
    return get_visible_booking_or_404(booking_id, principal)


def list_pending_bookings(principal) -> QuerySet[Booking]:
    # Returns bookings awaiting review or forwarding.
    return list_bookings(principal, status="pending")


def list_forwarded_bookings(principal) -> QuerySet[Booking]:
    # Returns bookings awaiting in-charge decision.
    return list_bookings(principal, status="forwarded")


def list_cancellation_requests(principal) -> QuerySet[Booking]:
    # Returns bookings where cancellation has been requested.
    return list_bookings(principal, status="cancellation_requested")
