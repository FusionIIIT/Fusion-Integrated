from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave_rules import (
    LeaveRuleError,
    convert_unused_vl_to_el,
    inclusive_calendar_days,
    validate_date_range,
    validate_sufficient_balance,
)


@pytest.mark.parametrize(
    ("unused_vl", "expected_el"),
    [
        ("60", "30"),
        ("5", "2.5"),
        ("1", "0.5"),
        ("0.5", "0.25"),
        ("0", "0"),
    ],
)
def test_vl_to_el_conversion_preserves_fractions(unused_vl, expected_el):
    assert convert_unused_vl_to_el(Decimal(unused_vl)) == Decimal(expected_el)


@pytest.mark.parametrize("unused_vl", ["-1", "NaN", "Infinity"])
def test_vl_conversion_rejects_invalid_balances(unused_vl):
    with pytest.raises(LeaveRuleError):
        convert_unused_vl_to_el(Decimal(unused_vl))


def test_date_range_counts_both_start_and_end_dates():
    assert inclusive_calendar_days(date(2026, 12, 30), date(2027, 1, 2)) == 4


def test_date_range_rejects_end_before_start():
    with pytest.raises(LeaveRuleError):
        validate_date_range(date(2026, 5, 10), date(2026, 5, 9))


def test_leave_request_within_balance_is_valid():
    validate_sufficient_balance(Decimal("10"), Decimal("2.5"))


@pytest.mark.parametrize(
    ("available", "requested"),
    [
        ("2", "3"),
        ("10", "0"),
        ("10", "-1"),
        ("-1", "1"),
    ],
)
def test_invalid_leave_balance_or_request_is_rejected(available, requested):
    with pytest.raises(LeaveRuleError):
        validate_sufficient_balance(Decimal(available), Decimal(requested))
