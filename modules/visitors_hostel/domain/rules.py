"""Small, deterministic rules shared by services and tests."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .errors import GuardFailed

CATEGORIES = frozenset({"A", "B", "C", "D"})
BILLING_RESPONSIBILITIES = frozenset({"Visitor", "Indenter", "Institute", "Project"})
INDIVIDUAL_MEALS = frozenset({"Breakfast", "Lunch", "Dinner"})
MEAL_ADDONS = frozenset({"Tea", "Milk"})


def cancellation_charge(*, arrival_date: date, cancellation_date: date,
                        one_day_room_rent: Decimal, no_show: bool = False) -> Decimal:
    """BR-VH-006..009; exact-seven-day case is explicitly free."""
    if one_day_room_rent < 0:
        raise GuardFailed("Room rent cannot be negative.")
    if no_show or cancellation_date == arrival_date:
        rate = Decimal("0.50")
    else:
        days_before = (arrival_date - cancellation_date).days
        if days_before < 0:
            raise GuardFailed("Cancellation must occur before arrival.")
        if days_before == 7 or days_before > 7:
            rate = Decimal("0")
        elif days_before < 7:
            rate = Decimal("0.25")
        else:  # Defensive; all integer day distances are handled above.
            rate = Decimal("0")
    return (one_day_room_rent * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_booking(*, category: str, billing_responsibility: str,
                     arrival_date: date, departure_date: date,
                     rooms: int, occupants: int) -> None:
    if category not in CATEGORIES:
        raise GuardFailed("Visitor category must be A, B, C, or D.")
    if billing_responsibility not in BILLING_RESPONSIBILITIES:
        raise GuardFailed("Invalid billing responsibility.")
    if departure_date <= arrival_date:
        raise GuardFailed("Departure must be after arrival.")
    if rooms < 1 or occupants < 1:
        raise GuardFailed("Room and occupant counts must be positive.")


def validate_meals(*, options: list[str], add_ons: list[str],
                   stay_start: date, stay_end: date, meal_date: date) -> None:
    if any(option not in INDIVIDUAL_MEALS | {"Full day"} for option in options):
        raise GuardFailed("Individual meals are Breakfast, Lunch, or Dinner.")
    if "Full day" in options and len(options) != 1:
        raise GuardFailed("Full day cannot be combined with individual meals.")
    if any(add_on not in MEAL_ADDONS for add_on in add_ons):
        raise GuardFailed("Meal add-ons are Tea or Milk.")
    if not stay_start <= meal_date < stay_end:
        raise GuardFailed("Meal date must fall within the guest stay.")
