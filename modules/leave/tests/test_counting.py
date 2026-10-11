from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain.counting import calculate_leave_days


def test_half_day_cl_counting_br_el_010():
    # BR-EL-010: Half-day CL consumes exactly 0.5 day
    days = calculate_leave_days(
        start_date=date(2026, 10, 15),
        end_date=date(2026, 10, 15),
        is_continuous=False,
        is_half_day=True,
    )
    assert days == Decimal("0.5")


def test_half_day_spanning_multiple_dates_raises():
    with pytest.raises(ValueError, match="Half-day leave must have identical"):
        calculate_leave_days(
            start_date=date(2026, 10, 15),
            end_date=date(2026, 10, 16),
            is_continuous=False,
            is_half_day=True,
        )


def test_continuous_day_counting_includes_weekends_and_holidays_br_el_011():
    # BR-EL-011: EL, COL, VL count weekends and closed holidays
    # Friday 2026-10-16 to Monday 2026-10-19 = 4 calendar days
    closed_holidays = {date(2026, 10, 19)}
    days = calculate_leave_days(
        start_date=date(2026, 10, 16),
        end_date=date(2026, 10, 19),
        is_continuous=True,
        closed_holidays=closed_holidays,
    )
    assert days == Decimal("4.0")


def test_working_day_counting_excludes_weekends_and_holidays_br_el_011():
    # BR-EL-011: CL, SCL, RH exclude weekends and closed holidays
    # Friday 2026-10-16 (Fri), 17 (Sat), 18 (Sun), 19 (Mon - closed holiday)
    # Only Friday should count = 1.0 day
    closed_holidays = {date(2026, 10, 19)}
    days = calculate_leave_days(
        start_date=date(2026, 10, 16),
        end_date=date(2026, 10, 19),
        is_continuous=False,
        closed_holidays=closed_holidays,
    )
    assert days == Decimal("1.0")
