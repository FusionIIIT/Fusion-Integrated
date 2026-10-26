from datetime import date

import pytest

from modules.leave.domain.rules import LeaveRuleError, requested_days, validate_request


def test_requested_days_counts_weekdays_inclusive():
    assert requested_days(date(2026, 10, 26), date(2026, 10, 30)) == 5


def test_weekend_only_range_has_no_workdays():
    assert requested_days(date(2026, 10, 31), date(2026, 11, 1)) == 0


def test_reversed_dates_are_rejected():
    with pytest.raises(LeaveRuleError, match="on or after"):
        requested_days(date(2026, 10, 27), date(2026, 10, 26))


def test_zero_workday_request_is_rejected():
    with pytest.raises(LeaveRuleError, match="no working days"):
        validate_request(date(2026, 10, 31), date(2026, 11, 1), 10)


def test_request_cannot_exceed_available_balance():
    with pytest.raises(LeaveRuleError, match="exceeds the available"):
        validate_request(date(2026, 10, 26), date(2026, 10, 28), 2)
