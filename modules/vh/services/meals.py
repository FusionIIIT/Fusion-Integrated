# Mess and meal management services for staying guests.
from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, DomainError, NotFoundError
from modules.vh.domain.rules import validate_meal_date_within_stay, validate_meal_selection
from modules.vh.domain.tariffs import lookup_meal_rate
from modules.vh.models.booking import Booking
from modules.vh.models.meal import MealBooking


@transaction.atomic
def book_meal(
    booking_id: int,
    meal_date: date,
    meal_option: str,
    individual_type: str | None,
    add_on_type: str | None,
    quantity: int,
    principal,
) -> MealBooking:
    # CFR-VH-010, BR-VH-025..032: Books meals for guests actively staying in VH.
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None

    if booking.status not in {"approved", "approved_offline", "room_allotted", "checked_in"}:
        raise ConflictError(
            f"Cannot book meals for booking in status '{booking.status}'. Active stay required."
        )

    if isinstance(meal_date, str):
        meal_date = date.fromisoformat(meal_date)

    try:
        validate_meal_date_within_stay(meal_date, booking.arrival_date, booking.departure_date)
        validate_meal_selection(meal_option, individual_type, add_on_type)
    except ValueError as err:
        raise DomainError(str(err)) from None

    if quantity < 1:
        raise BadRequestError("Meal quantity must be at least 1.")

    sub_opt = (individual_type or add_on_type or "").strip().lower()
    rate = lookup_meal_rate(meal_option, sub_opt)
    amount = rate * Decimal(quantity)

    return MealBooking.objects.create(
        booking=booking,
        meal_date=meal_date,
        meal_option=meal_option.strip().lower(),
        individual_type=individual_type.strip().lower() if individual_type else "",
        add_on_type=add_on_type.strip().lower() if add_on_type else "",
        quantity=quantity,
        rate=rate,
        amount=amount,
    )
