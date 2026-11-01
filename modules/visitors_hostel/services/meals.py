from decimal import Decimal

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.visitors_hostel.domain.rules import validate_meals
from modules.visitors_hostel.models import Booking, MealBooking, MealRate


def create_meal_booking(*, booking_id, actor, meal_date, options, add_ons, quantity):
    if not actor.has_permission("visitor_hostel.meal.manage"):
        raise PermissionDeniedError()
    booking = Booking.objects.filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    if booking.status != "checked_in":
        raise ConflictError("Meals may be recorded only for a guest currently staying in VH.",
                            code="guest_not_staying")
    try:
        validate_meals(options=options, add_ons=add_ons,
                       stay_start=booking.arrival_date,
                       stay_end=booking.departure_date, meal_date=meal_date)
    except ValueError as exc:
        raise ConflictError(str(exc), code="invalid_meal_booking") from exc
    rates = MealRate.objects.filter(active=True, effective_from__lte=meal_date,
                                    option__in=options + add_ons).order_by(
                                        "option", "-effective_from")
    latest = {}
    for rate in rates:
        latest.setdefault(rate.option, rate.rate)
    requested = set(options + add_ons)
    if set(latest) != requested:
        raise ConflictError("A meal option does not have an effective configured rate.",
                            code="meal_rate_missing")
    unit_rate = sum(latest.values(), Decimal("0"))
    return MealBooking.objects.create(
        booking=booking, meal_date=meal_date, options=options,
        add_ons=add_ons, quantity=quantity, unit_rate=unit_rate)
