"""Meal booking rules (BR-VH-025, BR-VH-029..031)."""
from __future__ import annotations

from datetime import date

FULL_DAY = "full_day"
INDIVIDUAL = "individual"
ADD_ON = "add_on"
KINDS = (FULL_DAY, INDIVIDUAL, ADD_ON)

BREAKFAST, LUNCH, DINNER = "breakfast", "lunch", "dinner"
TEA, MILK = "tea", "milk"
INDIVIDUAL_ITEMS = (BREAKFAST, LUNCH, DINNER)      # BR-VH-029
ADD_ON_ITEMS = (TEA, MILK)                         # BR-VH-030

#: Every priced item; a full-day meal is priced as one item of its own.
PRICED_ITEMS = (FULL_DAY, *INDIVIDUAL_ITEMS, *ADD_ON_ITEMS)


class InvalidMeal(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def priced_item(kind: str, item: str) -> str:
    """The tariff item for a booking line, or InvalidMeal."""
    if kind == FULL_DAY:
        if item:
            raise InvalidMeal("A full-day meal does not take an item.",
                              "full_day_has_item")
        return FULL_DAY
    if kind == INDIVIDUAL:
        if item not in INDIVIDUAL_ITEMS:
            raise InvalidMeal("An individual meal must be breakfast, lunch or dinner.",
                              "invalid_individual_meal")
        return item
    if kind == ADD_ON:
        if item not in ADD_ON_ITEMS:
            raise InvalidMeal("An add-on must be tea or milk.", "invalid_add_on")
        return item
    raise InvalidMeal("Meal kind must be full_day, individual or add_on.",
                      "invalid_meal_kind")


def within_stay(meal_date: date, stay_from: date, stay_to: date) -> None:
    """BR-VH-031: a meal belongs to a day of the guest's recorded stay."""
    if not stay_from <= meal_date <= stay_to:
        raise InvalidMeal(
            f"Meals can only be booked for {stay_from.isoformat()} to "
            f"{stay_to.isoformat()}, the guest's recorded stay.",
            "outside_stay")
