"""Unit tests for MMS pure Python business rules."""

import datetime

import pytest

from modules.mms.domain import rules
from modules.mms.domain.constants import MessRole, RebateStatus


def test_rebate_request_validation_success():
    submission_date = datetime.date(2026, 11, 1)
    start_date = datetime.date(2026, 11, 3)
    end_date = datetime.date(2026, 11, 7)

    duration = rules.validate_rebate_request(start_date, end_date, submission_date)
    assert duration == 4


def test_rebate_request_duration_less_than_minimum():
    submission_date = datetime.date(2026, 11, 1)
    start_date = datetime.date(2026, 11, 3)
    end_date = datetime.date(2026, 11, 4)

    with pytest.raises(ValueError, match="fewer than 3 days"):
        rules.validate_rebate_request(start_date, end_date, submission_date)


def test_rebate_request_lead_time_violation():
    submission_date = datetime.date(2026, 11, 2)
    start_date = datetime.date(2026, 11, 2)
    end_date = datetime.date(2026, 11, 5)

    with pytest.raises(ValueError, match="at least one calendar day before"):
        rules.validate_rebate_request(start_date, end_date, submission_date)


def test_rebate_request_end_before_start():
    submission_date = datetime.date(2026, 11, 1)
    start_date = datetime.date(2026, 11, 5)
    end_date = datetime.date(2026, 11, 3)

    with pytest.raises(ValueError, match="cannot be after end date"):
        rules.validate_rebate_request(start_date, end_date, submission_date)


def test_rebate_overlap_detection():
    existing = [
        {
            "id": 1,
            "start_date": datetime.date(2026, 11, 10),
            "end_date": datetime.date(2026, 11, 15),
            "status": RebateStatus.APPROVED.value,
        },
        {
            "id": 2,
            "start_date": datetime.date(2026, 12, 1),
            "end_date": datetime.date(2026, 12, 5),
            "status": RebateStatus.REJECTED.value,
        },
    ]

    # Non-overlapping
    rules.check_rebate_overlap(existing, datetime.date(2026, 11, 16), datetime.date(2026, 11, 20))

    # Overlapping start
    with pytest.raises(ValueError, match="impermissibly overlaps"):
        rules.check_rebate_overlap(
            existing, datetime.date(2026, 11, 14), datetime.date(2026, 11, 18)
        )

    # Edge-case: same-day boundary overlap (Nov 15)
    with pytest.raises(ValueError, match="impermissibly overlaps"):
        rules.check_rebate_overlap(
            existing, datetime.date(2026, 11, 15), datetime.date(2026, 11, 18)
        )


def test_exact_three_day_minimum_boundary():
    # Exactly 3 calendar days: Nov 3, Nov 4, Nov 5
    submission_date = datetime.date(2026, 11, 1)
    start_date = datetime.date(2026, 11, 3)
    end_date = datetime.date(2026, 11, 5)

    duration = rules.validate_rebate_request(start_date, end_date, submission_date)
    assert duration == 3


def test_registration_window_validation():
    window_start = datetime.date(2026, 11, 1)
    window_end = datetime.date(2026, 11, 10)

    rules.validate_registration_window(
        window_start, window_end, datetime.date(2026, 11, 5), is_open=True
    )

    with pytest.raises(ValueError, match="currently closed"):
        rules.validate_registration_window(
            window_start, window_end, datetime.date(2026, 11, 5), is_open=False
        )

    with pytest.raises(ValueError, match="outside the open window"):
        rules.validate_registration_window(
            window_start, window_end, datetime.date(2026, 11, 11), is_open=True
        )


def test_role_assignment_validation():
    rules.validate_role_assignment(MessRole.CARETAKER.value, employee_id=101)
    rules.validate_role_assignment(MessRole.WARDEN.value, employee_id=102)

    with pytest.raises(ValueError, match="Invalid mess role"):
        rules.validate_role_assignment("invalid_role", employee_id=101)

    with pytest.raises(ValueError, match="valid positive employee_id"):
        rules.validate_role_assignment(MessRole.CARETAKER.value, employee_id=0)
