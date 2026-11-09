"""Pure Python domain tests for leave day counting rules (BR-EL-010, BR-EL-011)."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.constants import LeaveCategory
from modules.elm.domain.counting import calculate_chargeable_days


def test_cl_full_day_working_days_only():
    """BR-EL-011: Casual Leave counts only working days, excluding weekends and closed holidays."""
    # 2026-10-12 (Monday) to 2026-10-16 (Friday) = 5 working days
    start = date(2026, 10, 12)
    end = date(2026, 10, 16)
    days = calculate_chargeable_days(LeaveCategory.CL, start, end)
    assert days == Decimal("5.00")

    # Span including weekend: 2026-10-16 (Friday) to 2026-10-19 (Monday) = 2 working days (Sat & Sun excluded)
    end_over_weekend = date(2026, 10, 19)
    days_weekend = calculate_chargeable_days(LeaveCategory.CL, date(2026, 10, 16), end_over_weekend)
    assert days_weekend == Decimal("2.00")


def test_cl_with_closed_holiday_excluded():
    """BR-EL-011: Closed holidays falling within CL are excluded."""
    # Monday to Wednesday (3 calendar days), Tuesday is closed holiday -> 2 chargeable days
    start = date(2026, 10, 12)
    end = date(2026, 10, 14)
    holiday = {date(2026, 10, 13)}
    days = calculate_chargeable_days(LeaveCategory.CL, start, end, closed_holidays=holiday)
    assert days == Decimal("2.00")


def test_cl_half_day_chargeable_half():
    """BR-EL-010: Half-day CL charges exactly 0.5 days."""
    single_day = date(2026, 10, 14)
    days = calculate_chargeable_days(
        LeaveCategory.CL,
        single_day,
        single_day,
        is_half_day=True,
    )
    assert days == Decimal("0.50")


def test_cl_half_day_multi_day_raises():
    """Half day CL must be on a single date."""
    with pytest.raises(ValueError, match="Half-day leave must start and end on the same date"):
        calculate_chargeable_days(
            LeaveCategory.CL,
            date(2026, 10, 14),
            date(2026, 10, 15),
            is_half_day=True,
        )


def test_rh_and_scl_working_days_only():
    """RH and SCL count only working days."""
    start = date(2026, 10, 16)  # Friday
    end = date(2026, 10, 19)    # Monday
    days_scl = calculate_chargeable_days(LeaveCategory.SCL, start, end)
    assert days_scl == Decimal("2.00")


def test_continuous_counting_el_col_vl():
    """BR-EL-011: EL, COL, and VL count continuously including weekends and closed holidays."""
    start = date(2026, 10, 16)  # Friday
    end = date(2026, 10, 19)    # Monday
    closed_holidays = {date(2026, 10, 17)}  # Saturday is holiday

    # 4 continuous calendar days: Fri, Sat, Sun, Mon
    for cat in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
        days = calculate_chargeable_days(cat, start, end, closed_holidays=closed_holidays)
        assert days == Decimal("4.00"), f"Failed continuous counting for {cat}"


def test_start_after_end_raises():
    with pytest.raises(ValueError, match="End date cannot be earlier than start date"):
        calculate_chargeable_days(LeaveCategory.CL, date(2026, 10, 20), date(2026, 10, 10))
