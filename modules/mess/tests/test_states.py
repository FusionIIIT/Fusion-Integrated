import pytest
from modules.mess.domain.states import can_transition, allowed_next
from datetime import datetime
from decimal import Decimal

@pytest.mark.parametrize(
    "current_state, next_state",
    [
        ("REGISTRATION_PENDING", "APPROVED"),
        ("PENDING", "PENDING"),
        ("APPROVED", "REJECTED"),
        ("DEREGISTRATION_APPROVED_AWAITING_EFFECTIVE", "EFFECTIVE"),
        ("REJECTED", "EFFECTIVE"),
        ("REBATE_PENDING", "REJECTED"),
        ("SPECIAL_FOOD_REQUESTED", "SERVED"),
        ("APPROVED", "SERVED"),
        ("APPROVED", "CANCELLED"),
        ("REJECTED", "SERVED"),
        ("BILL_GENERATED", "PUBLISHED"),
        ("GENERATED", "FINALIZED"),
    ],
)
def test_can_transition(current_state, next_state):
    assert can_transition(current_state, next_state)

@pytest.mark.parametrize(
    "current_state, allowed_next",
    [
        ("REGISTRATION_PENDING", ["APPROVED"]),
        ("PENDING", ["PENDING"]),
        ("APPROVED", ["REJECTED", "SERVED", "CANCELLED"]),
        ("DEREGISTRATION_APPROVED_AWAITING_EFFECTIVE", ["EFFECTIVE"]),
        ("REJECTED", ["EFFECTIVE"]),
        ("REBATE_PENDING", ["REJECTED"]),
        ("SPECIAL_FOOD_REQUESTED", ["SERVED"]),
        ("APPROVED", ["SERVED", "CANCELLED"]),
        ("BILL_GENERATED", ["PUBLISHED"]),
        ("GENERATED", ["FINALIZED"]),
    ],
)
def test_allowed_next(current_state, allowed_next):
    assert allowed_next(current_state) in allowed_next
