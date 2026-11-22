from datetime import time
from decimal import Decimal

import pytest

from modules.gymkhana.domain.constants import STATUS_CONFIRMED, STATUS_OPEN
from modules.gymkhana.domain.state_machine import transition_club, transition_membership
from modules.gymkhana.domain.validation import (
    validate_booking_time_range,
    validate_budget_amount,
    validate_poll_choices,
    validate_venue,
)


def test_club_state_machine_valid():
    assert transition_club(STATUS_OPEN, "confirm") == STATUS_CONFIRMED


def test_club_state_machine_invalid():
    with pytest.raises(ValueError, match="Illegal club state transition"):
        transition_club(STATUS_CONFIRMED, "confirm")


def test_membership_state_machine_valid():
    assert transition_membership(STATUS_OPEN, "approve") == STATUS_CONFIRMED


def test_membership_state_machine_invalid():
    with pytest.raises(ValueError, match="Illegal membership transition"):
        transition_membership(STATUS_CONFIRMED, "approve")


def test_validate_booking_time_range_valid():
    validate_booking_time_range(time(10, 0), time(11, 0))


def test_validate_booking_time_range_invalid():
    with pytest.raises(ValueError, match="start time must be earlier"):
        validate_booking_time_range(time(12, 0), time(11, 0))


def test_validate_venue_valid():
    validate_venue("CC1")


def test_validate_venue_invalid():
    with pytest.raises(ValueError, match="not a configured Gymkhana venue"):
        validate_venue("Unconfigured_Hall")


def test_validate_poll_choices_valid():
    validate_poll_choices(["Option A", "Option B"])


def test_validate_poll_choices_too_few():
    with pytest.raises(ValueError, match="at least two choices"):
        validate_poll_choices(["Only One"])


def test_validate_budget_amount_valid():
    validate_budget_amount(Decimal("100.50"))
    validate_budget_amount(0)


def test_validate_budget_amount_negative():
    with pytest.raises(ValueError, match="non-negative"):
        validate_budget_amount(Decimal("-10.00"))
