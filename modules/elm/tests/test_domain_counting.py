import datetime
from decimal import Decimal

import pytest

from modules.elm.domain.counting import calculate_chargeable_days


def test_half_day_cl_deduction():
    """BR-EL-010: Half-day CL consumes exactly 0.5 CL day."""
    date = datetime.date(2026, 11, 2)  # Monday
    days = calculate_chargeable_days("CL", date, date, half_day=True)
    assert days == Decimal("0.5")


def test_half_day_disallowed_for_multi_day_or_other_category():
    """BR-EL-010: Half-day option is only allowed for single-day CL."""
    d1 = datetime.date(2026, 11, 2)
    d2 = datetime.date(2026, 11, 3)
    with pytest.raises(ValueError, match="only applicable to single-day"):
        calculate_chargeable_days("CL", d1, d2, half_day=True)

    with pytest.raises(ValueError, match="only applicable to single-day"):
        calculate_chargeable_days("EL", d1, d1, half_day=True)


def test_cl_scl_rh_excludes_weekends_and_closed_holidays():
    """BR-EL-011: For CL, SCL, and RH, intervening weekends and closed holidays do not count."""
    # From Friday 2026-11-06 to Monday 2026-11-09:
    # Fri (working), Sat (weekend), Sun (weekend), Mon (working).
    # Plus closed holiday on Monday 2026-11-09.
    start = datetime.date(2026, 11, 6)
    end = datetime.date(2026, 11, 9)
    holiday = datetime.date(2026, 11, 9)

    days_cl = calculate_chargeable_days("CL", start, end, closed_holidays={holiday})
    # Only Friday counts = 1 day
    assert days_cl == Decimal("1")

    days_scl = calculate_chargeable_days("SCL", start, end, closed_holidays={holiday})
    assert days_scl == Decimal("1")

    days_rh = calculate_chargeable_days("RH", start, end, closed_holidays={holiday})
    assert days_rh == Decimal("1")


def test_el_col_vl_continuous_day_counting():
    """BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays count as leave days."""
    # From Friday 2026-11-06 to Monday 2026-11-09: 4 continuous days.
    start = datetime.date(2026, 11, 6)
    end = datetime.date(2026, 11, 9)
    holiday = datetime.date(2026, 11, 9)

    for cat in ("EL", "COL", "VL"):
        days = calculate_chargeable_days(cat, start, end, closed_holidays={holiday})
        assert days == Decimal("4")
