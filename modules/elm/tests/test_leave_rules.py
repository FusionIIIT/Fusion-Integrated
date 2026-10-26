from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave_rules import (
    annual_entitlement,
    convert_vacation_leave_to_earned_leave,
    count_leave_days,
    validate_no_overlap,
)


def test_annual_entitlements():
    assert annual_entitlement("CL") == Decimal("8")
    assert annual_entitlement("RH") == Decimal("2")
    assert annual_entitlement("SCL") == Decimal("15")
    assert annual_entitlement("EL") == Decimal("30")
    assert annual_entitlement("COL") == Decimal("20")
    assert annual_entitlement("VL") == Decimal("60")


def test_continuous_leave_counts_weekends_and_end_date():
    assert count_leave_days(
        date(2026, 10, 23), date(2026, 10, 26), "EL"
    ) == Decimal("4")


def test_invalid_date_range_is_rejected():
    with pytest.raises(ValueError):
        count_leave_days(date(2026, 10, 26), date(2026, 10, 23), "EL")


def test_cl_does_not_use_continuous_day_counting():
    with pytest.raises(ValueError):
        count_leave_days(date(2026, 10, 23), date(2026, 10, 23), "CL")


def test_overlapping_leave_is_rejected():
    with pytest.raises(ValueError):
        validate_no_overlap(
            date(2026, 10, 24),
            date(2026, 10, 26),
            [(date(2026, 10, 25), date(2026, 10, 27))],
        )


def test_non_overlapping_leave_is_allowed():
    validate_no_overlap(
        date(2026, 10, 28),
        date(2026, 10, 30),
        [(date(2026, 10, 25), date(2026, 10, 27))],
    )


def test_vacation_leave_conversion():
    assert convert_vacation_leave_to_earned_leave(
        Decimal("15")
    ) == Decimal("7.5")


def test_negative_vacation_balance_is_rejected():
    with pytest.raises(ValueError):
        convert_vacation_leave_to_earned_leave(Decimal("-1"))
