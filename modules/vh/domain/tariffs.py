# Pure Python calculation for tariffs and bills.
from decimal import Decimal
from typing import NamedTuple


class TariffKey(NamedTuple):
    category: str
    room_type: str
    occupancy: str


# Default institutional fallback daily tariffs (Category A, B, C, D)
DEFAULT_TARIFFS: dict[TariffKey, Decimal] = {
    TariffKey("A", "suite", "single"): Decimal("800.00"),
    TariffKey("A", "suite", "double"): Decimal("1000.00"),
    TariffKey("A", "non_suite", "single"): Decimal("500.00"),
    TariffKey("A", "non_suite", "double"): Decimal("700.00"),
    TariffKey("B", "suite", "single"): Decimal("1200.00"),
    TariffKey("B", "suite", "double"): Decimal("1500.00"),
    TariffKey("B", "non_suite", "single"): Decimal("800.00"),
    TariffKey("B", "non_suite", "double"): Decimal("1000.00"),
    TariffKey("C", "suite", "single"): Decimal("1600.00"),
    TariffKey("C", "suite", "double"): Decimal("2000.00"),
    TariffKey("C", "non_suite", "single"): Decimal("1100.00"),
    TariffKey("C", "non_suite", "double"): Decimal("1400.00"),
    TariffKey("D", "suite", "single"): Decimal("2200.00"),
    TariffKey("D", "suite", "double"): Decimal("2800.00"),
    TariffKey("D", "non_suite", "single"): Decimal("1500.00"),
    TariffKey("D", "non_suite", "double"): Decimal("1900.00"),
}

DEFAULT_MEAL_PRICES: dict[str, Decimal] = {
    "full_day": Decimal("300.00"),
    "breakfast": Decimal("70.00"),
    "lunch": Decimal("120.00"),
    "dinner": Decimal("120.00"),
    "tea": Decimal("15.00"),
    "milk": Decimal("25.00"),
}


def lookup_default_tariff(category: str, room_type: str, occupancy: str) -> Decimal:
    # BR-VH-023: Selects default tariff based on category, room type, and occupancy.
    key = TariffKey(category.upper(), room_type.lower(), occupancy.lower())
    return DEFAULT_TARIFFS.get(key, Decimal("1000.00"))


def lookup_meal_rate(option: str, sub_option: str = "") -> Decimal:
    # Looks up standard meal rate for bill calculation.
    opt = option.lower()
    if opt == "full_day":
        return DEFAULT_MEAL_PRICES["full_day"]
    sub = sub_option.lower()
    return DEFAULT_MEAL_PRICES.get(sub, Decimal("50.00"))
