"""Pure-python unit tests for ELM domain rules and state machine."""
import datetime

import pytest

from modules.elm.domain.errors import InvalidDateRangeError, InvalidTransitionError
from modules.elm.domain.state_machine import (
    TERMINAL_STATUSES,
    LeaveStatus,
    validate_dates,
    validate_transition,
)


def test_valid_transitions_from_pending():
    for target in (LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.CANCELLED):
        validate_transition(LeaveStatus.PENDING, target)


def test_cannot_transition_from_terminal_states():
    for terminal in TERMINAL_STATUSES:
        with pytest.raises(InvalidTransitionError):
            validate_transition(terminal, LeaveStatus.APPROVED)
        with pytest.raises(InvalidTransitionError):
            validate_transition(terminal, LeaveStatus.PENDING)


def test_invalid_target_transition():
    with pytest.raises(InvalidTransitionError):
        validate_transition(LeaveStatus.PENDING, "unknown_status")


def test_date_range_validation_succeeds_on_valid_dates():
    d1 = datetime.date(2026, 11, 1)
    d2 = datetime.date(2026, 11, 5)
    validate_dates(d1, d2)
    validate_dates(d1, d1)  # single day leave is valid


def test_date_range_validation_fails_on_inverted_dates():
    d1 = datetime.date(2026, 11, 5)
    d2 = datetime.date(2026, 11, 1)
    with pytest.raises(InvalidDateRangeError):
        validate_dates(d1, d2)
