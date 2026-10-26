from datetime import date

import pytest

from modules.elm.domain.policy import (
    check_date_overlap,
    is_valid_transition,
    requested_days,
    validate_balance_sufficiency,
    validate_substitute_eligibility,
)


def test_validate_substitute_eligibility():
    # Valid nomination: applicant is not substitute
    assert validate_substitute_eligibility(1, 2) is None

    # Invalid: applicant is self-nominated (BR-EL-014)
    with pytest.raises(ValueError, match=r"Applicant cannot be their own substitute\."):
        validate_substitute_eligibility(1, 1)


def test_check_date_overlap():
    # Overlapping intervals: partial overlap (BR-EL-012)
    assert check_date_overlap(
        date(2023, 10, 1), date(2023, 10, 5), date(2023, 10, 4), date(2023, 10, 8)
    )

    # Overlapping intervals: enclosed/nested
    assert check_date_overlap(
        date(2023, 10, 1), date(2023, 10, 10), date(2023, 10, 3), date(2023, 10, 5)
    )

    # Non-overlapping intervals: adjacent
    assert not check_date_overlap(
        date(2023, 10, 1), date(2023, 10, 5), date(2023, 10, 6), date(2023, 10, 10)
    )

    # Non-overlapping intervals: separate
    assert not check_date_overlap(
        date(2023, 10, 1), date(2023, 10, 5), date(2023, 10, 15), date(2023, 10, 20)
    )


def test_validate_balance_sufficiency():
    # Sufficient balance
    validate_balance_sufficiency(10, 5)

    # Exact balance
    validate_balance_sufficiency(5, 5)

    # Insufficient balance
    with pytest.raises(ValueError, match="Insufficient leave balance"):
        validate_balance_sufficiency(5, 10)


def test_is_valid_transition():
    # Allowed transitions
    assert is_valid_transition("AWAITING_SUBSTITUTE", "AWAITING_APPROVAL")
    assert is_valid_transition("AWAITING_SUBSTITUTE", "WITHDRAWN")
    assert is_valid_transition("AWAITING_APPROVAL", "APPROVED")
    assert is_valid_transition("AWAITING_APPROVAL", "REJECTED")
    assert is_valid_transition("AWAITING_APPROVAL", "WITHDRAWN")
    assert is_valid_transition("APPROVED", "CANCELLED")

    # Disallowed transitions
    assert not is_valid_transition("APPROVED", "REJECTED")
    assert not is_valid_transition("REJECTED", "APPROVED")
    assert not is_valid_transition("WITHDRAWN", "APPROVED")


def test_requested_days():
    # Correct day counts
    assert requested_days(date(2023, 10, 1), date(2023, 10, 5)) == 5
    assert requested_days(date(2023, 10, 1), date(2023, 10, 10)) == 10

    # Inverted dates should raise ValueError
    with pytest.raises(ValueError, match=r"End date cannot be earlier than start date\."):
        requested_days(date(2023, 10, 10), date(2023, 10, 1))
