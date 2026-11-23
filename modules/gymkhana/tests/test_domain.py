"""Domain logic unit tests for Gymkhana."""

import datetime
from decimal import Decimal

import pytest

from modules.gymkhana.domain.exceptions import DomainStateError, DomainValidationError
from modules.gymkhana.domain.state_machines import (
    transition_club,
    transition_membership,
    transition_poll,
)
from modules.gymkhana.domain.validation import (
    validate_booking_times,
    validate_budget_amount,
    validate_club_category,
    validate_club_is_confirmed,
    validate_distinct_leaders,
    validate_file_present,
    validate_poll_active,
    validate_poll_choices,
    validate_venue,
)


def test_validate_club_category():
    assert validate_club_category("Technical") == "technical"
    assert validate_club_category("SPORTS") == "sports"
    assert validate_club_category("cultural") == "cultural"
    with pytest.raises(DomainValidationError):
        validate_club_category("Academic")


def test_validate_distinct_leaders():
    validate_distinct_leaders(1, 2)
    with pytest.raises(DomainValidationError):
        validate_distinct_leaders(1, 1)


def test_validate_booking_times():
    t1 = datetime.time(10, 0)
    t2 = datetime.time(11, 0)
    validate_booking_times(t1, t2)
    with pytest.raises(DomainValidationError):
        validate_booking_times(t2, t1)
    with pytest.raises(DomainValidationError):
        validate_booking_times(t1, t1)


def test_validate_venue():
    venues = ["Hall 1", "SAC Gym"]
    assert validate_venue("Hall 1", venues) == "Hall 1"
    with pytest.raises(DomainValidationError):
        validate_venue("Unknown Arena", venues)


def test_validate_club_is_confirmed():
    validate_club_is_confirmed("confirmed")
    with pytest.raises(DomainValidationError):
        validate_club_is_confirmed("open")


def test_validate_poll_choices():
    assert validate_poll_choices(["Option A", "Option B"]) == ["Option A", "Option B"]
    with pytest.raises(DomainValidationError):
        validate_poll_choices(["Only One"])
    with pytest.raises(DomainValidationError):
        validate_poll_choices(["Duplicate", "Duplicate"])


def test_validate_poll_active():
    future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)
    past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
    validate_poll_active(future)
    with pytest.raises(DomainValidationError):
        validate_poll_active(past)


def test_validate_budget_amount():
    assert validate_budget_amount(100) == Decimal("100")
    assert validate_budget_amount(0) == Decimal("0")
    with pytest.raises(DomainValidationError):
        validate_budget_amount(-1)


def test_validate_file_present():
    validate_file_present(True, "supporting_file")
    with pytest.raises(DomainValidationError):
        validate_file_present(False, "supporting_file")


def test_state_machines():
    # Club transitions (BW-GYM-03)
    assert transition_club("open", "CONFIRM", "student_admin") == "confirmed"
    with pytest.raises(DomainStateError):
        transition_club("confirmed", "CONFIRM", "student_admin")
    with pytest.raises(DomainStateError):
        transition_club("open", "CONFIRM", "student")

    # Membership transitions (BW-GYM-01)
    assert transition_membership("open", "APPROVE", "club_head") == "confirmed"
    with pytest.raises(DomainStateError):
        transition_membership("confirmed", "APPROVE", "club_head")

    # Poll transitions (BW-GYM-02)
    assert transition_poll("active", "EXPIRE", "system") == "expired"
    with pytest.raises(DomainStateError):
        transition_poll("expired", "EXPIRE", "system")
