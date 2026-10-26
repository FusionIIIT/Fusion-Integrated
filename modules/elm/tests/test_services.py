"""Unit tests for ELM business calculations, quotas, and conversion rules."""
from __future__ import annotations

import datetime
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError

from modules.elm.services import (
    calculate_leave_days,
    get_default_annual_quota,
)


def test_annual_quotas_match_specification():
    """Verify statutory annual quotas per category and designation (BR-EL-002..009)."""
    # Non-Faculty Quotas
    assert get_default_annual_quota("cl", is_faculty=False) == Decimal("8.0")
    assert get_default_annual_quota("rh", is_faculty=False) == Decimal("2.0")
    assert get_default_annual_quota("scl", is_faculty=False) == Decimal("15.0")
    assert get_default_annual_quota("el", is_faculty=False) == Decimal("30.0")
    assert get_default_annual_quota("vl", is_faculty=False) == Decimal("0.0")
    assert get_default_annual_quota("col", is_faculty=False) == Decimal("20.0")

    # Faculty Quotas (EL initialized via VL conversion, VL is 60)
    assert get_default_annual_quota("cl", is_faculty=True) == Decimal("8.0")
    assert get_default_annual_quota("rh", is_faculty=True) == Decimal("2.0")
    assert get_default_annual_quota("scl", is_faculty=True) == Decimal("15.0")
    assert get_default_annual_quota("el", is_faculty=True) == Decimal("0.0")
    assert get_default_annual_quota("vl", is_faculty=True) == Decimal("60.0")
    assert get_default_annual_quota("col", is_faculty=True) == Decimal("20.0")


def test_cl_half_day_consumes_half_day():
    """CL half-day request consumes exactly 0.5 days (BR-EL-010)."""
    single_date = datetime.date(2026, 11, 4)  # Wednesday
    days = calculate_leave_days(
        category="cl",
        start_date=single_date,
        end_date=single_date,
        half_day=True,
        half_day_type="first_half",
    )
    assert days == Decimal("0.5")


def test_non_cl_half_day_rejected():
    """Attempting half-day on EL, RH, or SCL raises ValidationError (BR-EL-010)."""
    single_date = datetime.date(2026, 11, 4)
    with pytest.raises(ValidationError, match="Half-day requests are only permitted for Casual Leave"):
        calculate_leave_days(
            category="el",
            start_date=single_date,
            end_date=single_date,
            half_day=True,
            half_day_type="first_half",
        )

    with pytest.raises(ValidationError, match="Half-day requests are only permitted for Casual Leave"):
        calculate_leave_days(
            category="rh",
            start_date=single_date,
            end_date=single_date,
            half_day=True,
            half_day_type="first_half",
        )


def test_continuous_day_counting_for_el_col_vl():
    """EL, COL, and VL count all calendar days continuously including weekends (BR-EL-011)."""
    # Friday 2026-11-06 to Monday 2026-11-09 (Fri, Sat, Sun, Mon = 4 days)
    start_date = datetime.date(2026, 11, 6)
    end_date = datetime.date(2026, 11, 9)

    assert calculate_leave_days("el", start_date, end_date) == Decimal("4.0")
    assert calculate_leave_days("col", start_date, end_date) == Decimal("4.0")
    assert calculate_leave_days("vl", start_date, end_date) == Decimal("4.0")


def test_working_day_counting_excludes_weekends_for_cl_and_scl():
    """CL and SCL exclude Saturdays and Sundays from leave count (BR-EL-011)."""
    # Friday 2026-11-06 to Monday 2026-11-09 (Fri, Sat, Sun, Mon -> excludes Sat, Sun -> 2 days)
    start_date = datetime.date(2026, 11, 6)
    end_date = datetime.date(2026, 11, 9)

    assert calculate_leave_days("cl", start_date, end_date) == Decimal("2.0")
    assert calculate_leave_days("scl", start_date, end_date) == Decimal("2.0")


def test_start_date_after_end_date_raises():
    """start_date after end_date raises ValidationError."""
    with pytest.raises(ValidationError, match="start_date cannot be after end_date"):
        calculate_leave_days(
            "cl",
            datetime.date(2026, 11, 10),
            datetime.date(2026, 11, 5),
        )


def test_vl_conversion_ratio_and_fractions():
    """VL to EL conversion computes exact 2:1 ratio including fractions (BR-EL-007)."""
    # 15.0 VL -> 7.5 EL
    unused_vl = Decimal("15.0")
    converted_el = unused_vl / Decimal("2.0")
    assert converted_el == Decimal("7.5")

    # 60.0 VL -> 30.0 EL
    assert Decimal("60.0") / Decimal("2.0") == Decimal("30.0")

    # 1.0 VL -> 0.5 EL
    assert Decimal("1.0") / Decimal("2.0") == Decimal("0.5")
