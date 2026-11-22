# Domain unit tests: Pure Python validation and calculations with no database.
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.vh.domain.cancellation import (
    compute_cancellation_charge,
    compute_cancellation_percentage,
)
from modules.vh.domain.rules import (
    validate_billing_responsibility,
    validate_meal_date_within_stay,
    validate_meal_selection,
    validate_occupancy_type,
    validate_room_type,
    validate_stay_dates,
    validate_visitor_category,
)
from modules.vh.domain.tariffs import lookup_default_tariff, lookup_meal_rate


def test_br_vh_002_validate_billing_responsibility_valid():
    # BR-VH-002: Restricted to Visitor, Indenter, Institute, Project
    for val in ["visitor", "indenter", "institute", "project", "Visitor", "INSTITUTE"]:
        assert validate_billing_responsibility(val) in {
            "visitor",
            "indenter",
            "institute",
            "project",
        }


def test_br_vh_002_validate_billing_responsibility_invalid():
    # BR-VH-002: Rejects invalid billing responsibility
    with pytest.raises(ValueError, match="Invalid billing"):
        validate_billing_responsibility("third_party")


def test_br_vh_019_visitor_category_valid():
    # BR-VH-019: Categories A, B, C, D
    for cat in ["A", "B", "C", "D", "a", "b", "c", "d"]:
        assert validate_visitor_category(cat) in {"A", "B", "C", "D"}


def test_br_vh_019_visitor_category_invalid():
    # BR-VH-019: Rejects non A/B/C/D category
    with pytest.raises(ValueError, match="Invalid visitor category"):
        validate_visitor_category("E")


def test_br_vh_013_014_occupancy_types():
    # BR-VH-013, BR-VH-014: Single and Double occupancy
    assert validate_occupancy_type("single") == "single"
    assert validate_occupancy_type("Double") == "double"
    with pytest.raises(ValueError, match="Invalid occupancy type"):
        validate_occupancy_type("triple")


def test_br_vh_015_016_room_types():
    # BR-VH-015, BR-VH-016: Suite and Non-suite
    assert validate_room_type("suite") == "suite"
    assert validate_room_type("Non_Suite") == "non_suite"
    with pytest.raises(ValueError, match="Invalid room type"):
        validate_room_type("deluxe")


def test_stay_dates_validation():
    today = date.today()
    validate_stay_dates(today, today + timedelta(days=2))
    validate_stay_dates(today, today)
    with pytest.raises(ValueError, match="Departure date cannot precede"):
        validate_stay_dates(today + timedelta(days=2), today)


def test_br_vh_029_030_meal_options():
    # BR-VH-029: Individual meals restricted to Breakfast, Lunch, Dinner
    validate_meal_selection("full_day")
    validate_meal_selection("individual", individual_type="breakfast")
    validate_meal_selection("individual", individual_type="Lunch")
    validate_meal_selection("individual", individual_type="dinner")
    with pytest.raises(ValueError, match="Invalid individual meal"):
        validate_meal_selection("individual", individual_type="snacks")

    # BR-VH-030: Add-ons restricted to Tea and Milk
    validate_meal_selection("add_on", add_on_type="tea")
    validate_meal_selection("add_on", add_on_type="Milk")
    with pytest.raises(ValueError, match="Invalid add-on option"):
        validate_meal_selection("add_on", add_on_type="coffee")

    with pytest.raises(ValueError, match="Invalid meal option"):
        validate_meal_selection("buffet")


def test_br_vh_031_meal_date_within_stay():
    # BR-VH-031: Meal bookings linked to stay duration
    arr = date(2026, 11, 10)
    dep = date(2026, 11, 15)
    validate_meal_date_within_stay(date(2026, 11, 10), arr, dep)
    validate_meal_date_within_stay(date(2026, 11, 12), arr, dep)
    validate_meal_date_within_stay(date(2026, 11, 15), arr, dep)
    with pytest.raises(ValueError, match="outside stay duration"):
        validate_meal_date_within_stay(date(2026, 11, 9), arr, dep)
    with pytest.raises(ValueError, match="outside stay duration"):
        validate_meal_date_within_stay(date(2026, 11, 16), arr, dep)


def test_br_vh_006_to_009_cancellation_percentages():
    # BR-VH-007: Exactly 7 days before arrival = 0%
    today = date(2026, 11, 1)
    arrival_7d = date(2026, 11, 8)
    assert compute_cancellation_percentage(arrival_7d, today) == Decimal("0.00")

    # > 7 days before arrival = 0%
    arrival_10d = date(2026, 11, 11)
    assert compute_cancellation_percentage(arrival_10d, today) == Decimal("0.00")

    # BR-VH-008: Within 7 days (1 to 6 days) = 25%
    arrival_3d = date(2026, 11, 4)
    assert compute_cancellation_percentage(arrival_3d, today) == Decimal("25.00")
    arrival_1d = date(2026, 11, 2)
    assert compute_cancellation_percentage(arrival_1d, today) == Decimal("25.00")

    # BR-VH-009: Same-day = 50%
    arrival_0d = date(2026, 11, 1)
    assert compute_cancellation_percentage(arrival_0d, today) == Decimal("50.00")


def test_cancellation_charge_calculation():
    # Computes percentage of one-day room rent
    rent = Decimal("1000.00")
    assert compute_cancellation_charge(rent, Decimal("0.00")) == Decimal("0.00")
    assert compute_cancellation_charge(rent, Decimal("25.00")) == Decimal("250.00")
    assert compute_cancellation_charge(rent, Decimal("50.00")) == Decimal("500.00")
    assert compute_cancellation_charge(Decimal("0.00"), Decimal("50.00")) == Decimal("0.00")


def test_br_vh_023_tariffs_and_meal_pricing():
    # BR-VH-023: Default institutional category tariffs
    assert lookup_default_tariff("A", "suite", "single") == Decimal("800.00")
    assert lookup_default_tariff("B", "non_suite", "double") == Decimal("1000.00")
    assert lookup_default_tariff("D", "suite", "double") == Decimal("2800.00")
    # Meal price lookups
    assert lookup_meal_rate("full_day") == Decimal("300.00")
    assert lookup_meal_rate("individual", "breakfast") == Decimal("70.00")
    assert lookup_meal_rate("add_on", "tea") == Decimal("15.00")
