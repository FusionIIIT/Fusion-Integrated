# Scoping and row visibility for VHMS bookings.
from django.db.models import QuerySet

from core.api.exceptions import NotFoundError
from modules.vh.models.booking import Booking


def scope_bookings(queryset: QuerySet[Booking], principal) -> QuerySet[Booking]:
    # Restricts bookings to own records for indenters; full visibility for operational roles.
    perms = getattr(principal, "permissions", set())
    if "vh.booking.review" in perms or "vh.booking.approve" in perms:
        return queryset
    user_id = getattr(principal, "user_id", None)
    if user_id is None:
        return queryset.none()
    return queryset.filter(indenter_id=user_id)


def get_visible_booking_or_404(booking_id: int, principal) -> Booking:
    # Fetches booking within scoped visibility or raises NotFoundError (HTTP 404).
    scoped = scope_bookings(Booking.objects.all(), principal)
    try:
        return scoped.get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None
