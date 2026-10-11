"""The request rules, tested without a database (Step 5.3)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.elm.domain import policy

MONDAY = date(2026, 4, 6)                                  # a known Monday
CL = policy.LeaveTypeRules(code="CL", name="Casual Leave",
                           counts_calendar_days=False, allows_half_day=True,
                           requires_reason=False)
EL = policy.LeaveTypeRules(code="EL", name="Earned Leave",
                           counts_calendar_days=False, allows_half_day=False,
                           requires_reason=True)
CAL = policy.LeaveTypeRules(code="RH", name="Restricted Holiday",
                            counts_calendar_days=True, allows_half_day=False,
                            requires_reason=False)


def request(start, end, **kw):
    return policy.LeaveRequest(start_date=start, end_date=end, **kw)


class TestCounting:

    def test_a_full_week_counts_five_working_days(self):
        days = policy.count_days(request(MONDAY, MONDAY + timedelta(days=4)), CL, set())
        assert days == Decimal(5)

    def test_a_weekend_is_not_a_leave_day(self):
        saturday = MONDAY + timedelta(days=5)
        assert policy.working_days(saturday, saturday + timedelta(days=1), set()) == 0

    def test_a_holiday_inside_the_range_is_not_counted(self):
        days = policy.count_days(request(MONDAY, MONDAY + timedelta(days=1)), CL,
                                 {MONDAY + timedelta(days=1)})
        assert days == Decimal(1)

    def test_a_half_day_counts_a_half_day(self):
        assert policy.count_days(request(MONDAY, MONDAY, is_half_day=True), CL,
                                 set()) == policy.HALF_DAY

    def test_a_calendar_day_type_counts_the_weekend(self):
        days = policy.count_days(request(MONDAY, MONDAY + timedelta(days=6)), CAL,
                                 set())
        assert days == Decimal(7)


class TestValidation:

    def test_a_plain_request_passes(self):
        policy.validate_request(request(MONDAY, MONDAY + timedelta(days=1)), CL,
                                set(), MONDAY - timedelta(days=1))

    def test_dates_out_of_order_are_refused(self):
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(request(MONDAY, MONDAY - timedelta(days=1)),
                                    CL, set(), MONDAY)
        assert err.value.code == "dates_out_of_order"

    def test_a_span_beyond_the_limit_is_refused(self):
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(
                request(MONDAY, MONDAY + timedelta(days=policy.MAX_SPAN_DAYS)), CL,
                set(), MONDAY)
        assert err.value.code == "span_too_long"

    def test_backdating_beyond_the_limit_is_refused(self):
        old = MONDAY - timedelta(days=policy.BACKDATE_LIMIT_DAYS + 1)
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(request(old, old), CL, set(), MONDAY)
        assert err.value.code == "too_far_back"

    def test_backdating_within_the_limit_is_allowed(self):
        recent = MONDAY - timedelta(days=policy.BACKDATE_LIMIT_DAYS)
        policy.validate_request(request(recent, recent), CL, set(), MONDAY)

    def test_a_half_day_across_two_days_is_refused(self):
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(
                request(MONDAY, MONDAY + timedelta(days=1), is_half_day=True,
                        half_day_part="first"), CL, set(), MONDAY)
        assert err.value.code == "half_day_multiple_days"

    def test_a_half_day_without_a_part_is_refused(self):
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(request(MONDAY, MONDAY, is_half_day=True),
                                    CL, set(), MONDAY)
        assert err.value.code == "half_day_part_required"

    def test_a_half_day_on_a_type_that_forbids_it_is_refused(self):
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(
                request(MONDAY, MONDAY, is_half_day=True, half_day_part="second"),
                EL, set(), MONDAY)
        assert err.value.code == "half_day_not_allowed"

    def test_a_reason_required_type_refuses_a_blank_reason(self):
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(request(MONDAY, MONDAY), EL, set(), MONDAY)
        assert err.value.code == "reason_required"

    def test_a_reason_required_type_accepts_a_reason(self):
        policy.validate_request(request(MONDAY, MONDAY, reason="Medical"),
                                EL, set(), MONDAY)

    def test_a_weekend_only_range_is_refused(self):
        saturday = MONDAY + timedelta(days=5)
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(
                request(saturday, saturday + timedelta(days=1)), CL, set(), MONDAY)
        assert err.value.code == "no_working_days"

    def test_a_half_day_on_a_holiday_is_refused(self):
        with pytest.raises(policy.RuleViolation) as err:
            policy.validate_request(
                request(MONDAY, MONDAY, is_half_day=True, half_day_part="first"),
                CL, {MONDAY}, MONDAY)
        assert err.value.code == "no_working_days"
