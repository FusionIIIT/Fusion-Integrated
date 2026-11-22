# Billing selectors for VHMS.

from core.api.exceptions import NotFoundError
from modules.vh.models.bill import Bill
from modules.vh.selectors.scoping import get_visible_booking_or_404


def get_bill_for_booking(booking_id: int, principal) -> Bill:
    # Returns bill and line items for a booking or raises 404.
    booking = get_visible_booking_or_404(booking_id, principal)
    try:
        return (
            Bill.objects.prefetch_related("items").select_related("settlement").get(booking=booking)
        )
    except Bill.DoesNotExist:
        raise NotFoundError(f"Bill for booking {booking_id} does not exist.") from None
