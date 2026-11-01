from datetime import date
from decimal import Decimal

import pytest

from modules.visitors_hostel.domain import rules, state_machine as sm


def test_online_and_offline_requests_share_pending_approval_flow():
    assert sm.resolve(sm.PENDING, sm.FORWARDED, sm.CARETAKER).permission == \
        "visitor_hostel.booking.review"
    assert sm.resolve(sm.FORWARDED, sm.APPROVED, sm.IN_CHARGE).permission == \
        "visitor_hostel.booking.decide"


def test_in_charge_cannot_review_pending_request_directly():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.PENDING, sm.APPROVED, sm.IN_CHARGE)


def test_room_allotment_only_after_approval():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.PENDING, sm.ROOM_ALLOTTED, sm.CARETAKER)


@pytest.mark.parametrize("days, expected", [
    (7, "0.00"), (6, "25.00"), (1, "25.00"), (0, "50.00"), (10, "0.00")])
def test_cancellation_schedule(days, expected):
    result = rules.cancellation_charge(
        arrival_date=date(2026, 12, 20),
        cancellation_date=date(2026, 12, 20) - __import__("datetime").timedelta(days=days),
        one_day_room_rent=Decimal("100"))
    assert result == Decimal(expected)


def test_no_show_charge_is_half_daily_rent():
    assert rules.cancellation_charge(
        arrival_date=date(2026, 12, 20), cancellation_date=date(2026, 12, 21),
        one_day_room_rent=Decimal("200"), no_show=True) == Decimal("100.00")


def test_booking_value_enums_and_dates_are_validated():
    rules.validate_booking(category="A", billing_responsibility="Project",
        arrival_date=date(2026, 12, 1), departure_date=date(2026, 12, 2),
        rooms=1, occupants=2)
    with pytest.raises(rules.GuardFailed):
        rules.validate_booking(category="X", billing_responsibility="Visitor",
            arrival_date=date(2026, 12, 2), departure_date=date(2026, 12, 1),
            rooms=1, occupants=1)


def test_meals_are_limited_and_inside_stay():
    rules.validate_meals(options=["Breakfast", "Dinner"], add_ons=["Milk"],
        stay_start=date(2026, 12, 1), stay_end=date(2026, 12, 4),
        meal_date=date(2026, 12, 2))
    with pytest.raises(rules.GuardFailed):
        rules.validate_meals(options=["Brunch"], add_ons=[],
            stay_start=date(2026, 12, 1), stay_end=date(2026, 12, 4),
            meal_date=date(2026, 12, 2))
    with pytest.raises(rules.GuardFailed):
        rules.validate_meals(options=["Lunch"], add_ons=[],
            stay_start=date(2026, 12, 1), stay_end=date(2026, 12, 4),
            meal_date=date(2026, 12, 4))
