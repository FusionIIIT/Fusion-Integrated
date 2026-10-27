from datetime import date

import pytest

from modules.leave.domain.requests import LeaveRuleError, RequestPeriod, overlaps, validate_period


def test_opposite_half_day_cl_requests_do_not_overlap():
    first = RequestPeriod("cl", date(2026, 10, 12), date(2026, 10, 12), "first")
    second = RequestPeriod("cl", date(2026, 10, 12), date(2026, 10, 12), "second")
    assert overlaps(first, second) is False


def test_same_half_day_cl_requests_overlap():
    first = RequestPeriod("cl", date(2026, 10, 12), date(2026, 10, 12), "first")
    assert overlaps(first, first) is True


@pytest.mark.parametrize("period", [
    RequestPeriod("el", date(2026, 10, 12), date(2026, 10, 12), "full"),
    RequestPeriod("rh", date(2026, 10, 12), date(2026, 10, 12), "first"),
    RequestPeriod("cl", date(2026, 10, 12), date(2026, 10, 13), "first"),
])
def test_unsupported_or_invalid_periods_are_refused(period):
    with pytest.raises(LeaveRuleError):
        validate_period(period)
