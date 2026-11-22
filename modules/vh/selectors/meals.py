# Meal queries for VHMS.
from django.db.models import QuerySet

from modules.vh.models.meal import MealBooking
from modules.vh.selectors.scoping import get_visible_booking_or_404


def list_booking_meals(booking_id: int, principal) -> QuerySet[MealBooking]:
    # Returns meal bookings for a visible booking.
    booking = get_visible_booking_or_404(booking_id, principal)
    return MealBooking.objects.filter(booking=booking).order_by("meal_date", "id")
