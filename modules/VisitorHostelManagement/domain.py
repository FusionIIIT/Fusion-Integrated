"""Domain business logic and rules for Visitor Hostel Management (VHMS)."""
from datetime import date
from decimal import Decimal


def compute_cancellation_charge(check_in: date, cancel_date: date, rent: Decimal) -> Decimal:
    """Compute cancellation charges according to schedule (BR-VH-006..009)."""
    days = (check_in - cancel_date).days
    rate = Decimal(str(rent))
    if days >= 7:
        return Decimal("0.00")
    if days > 0:
        return (rate * Decimal("0.25")).quantize(Decimal("0.01"))
    return (rate * Decimal("0.50")).quantize(Decimal("0.01"))


def compute_stay_days(check_in: date, check_out: date) -> int:
    """Calculate the number of chargeable days between check-in and check-out."""
    return max(1, (check_out - check_in).days)


def compute_meal_cost(meal_type: str, add_on: str = "none") -> Decimal:
    """Calculate the cost of meals and optional add-ons (BR-VH-026..030)."""
    prices = {"breakfast": Decimal("50.00"), "lunch": Decimal("100.00"), "dinner": Decimal("100.00"), "full_day": Decimal("250.00")}
    addons = {"none": Decimal("0.00"), "tea": Decimal("10.00"), "milk": Decimal("15.00")}
    return prices.get(meal_type.lower(), Decimal("0.00")) + addons.get(add_on.lower(), Decimal("0.00"))


def check_date_overlap(start1: date, end1: date, start2: date, end2: date) -> bool:
    """Check if two date ranges overlap."""
    return start1 < end2 and start2 < end1


def is_no_show(status: str, check_in: date, today: date) -> bool:
    """Check if booking is an unacknowledged no-show (BR-VH-017)."""
    return status == "approved" and today > check_in


def is_overstay(status: str, check_out: date, today: date) -> bool:
    """Check if guest is overstaying past approved check-out (BR-VH-018)."""
    return status == "checked_in" and today > check_out


def is_inventory_low(qty: int, min_threshold: int) -> bool:
    """Check if inventory quantity is at or below threshold (BR-VH-041)."""
    return qty <= min_threshold
