from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain import rules

# --- Fixtures and Setup ---

@pytest.fixture
def weekend_dates():
    # Fri 2026-10-23 to Mon 2026-10-26
    return {
        "fri": date(2026, 10, 23),
        "sat": date(2026, 10, 24),
        "sun": date(2026, 10, 25),
        "mon": date(2026, 10, 26),
    }

# --- Test Entitlements ---

def test_get_annual_entitlement_standard():
    # CL, RH, SCL, COL are standard
    assert rules.get_annual_entitlement("CL") == Decimal("8.0")
    assert rules.get_annual_entitlement("RH") == Decimal("2.0")
    assert rules.get_annual_entitlement("SCL") == Decimal("15.0")
    assert rules.get_annual_entitlement("COL") == Decimal("20.0")

def test_get_annual_entitlement_non_faculty():
    # EL (Non-faculty)
    assert rules.get_annual_entitlement("EL", is_faculty=False) == Decimal("30.0")
    # VL (Non-faculty)
    assert rules.get_annual_entitlement("VL", is_faculty=False) == Decimal("0.0")

def test_get_annual_entitlement_faculty():
    # EL (Faculty)
    assert rules.get_annual_entitlement("EL", is_faculty=True) == Decimal("0.0")
    # VL (Faculty)
    assert rules.get_annual_entitlement("VL", is_faculty=True) == Decimal("60.0")

def test_get_annual_entitlement_unknown_code():
    with pytest.raises(rules.RuleViolation):
        rules.get_annual_entitlement("XX")

# --- Test Day Counting ---

def test_calculate_leave_days_end_before_start():
    start = date(2024, 10, 10)
    end = date(2024, 10, 1)
    with pytest.raises(rules.RuleViolation):
        rules.calculate_leave_days("EL", start, end)

def test_calculate_leave_days_unknown_category():
    start = date(2024, 10, 1)
    end = date(2024, 10, 2)
    with pytest.raises(rules.RuleViolation):
        rules.calculate_leave_days("XX", start, end)

def test_calculate_leave_days_el_full_range_includes_weekend(weekend_dates):
    # Fri 2026-10-23 to Mon 2026-10-26 (4 calendar days)
    start = weekend_dates["fri"]
    end = weekend_dates["mon"]
    # EL counts all calendar days
    assert rules.calculate_leave_days("EL", start, end) == Decimal("4.0")

def test_calculate_leave_days_cl_full_range_excludes_weekend(weekend_dates):
    # Fri 2026-10-23 to Mon 2026-10-26 (Fri and Mon count)
    start = weekend_dates["fri"]
    end = weekend_dates["mon"]
    # CL excludes Sat/Sun
    assert rules.calculate_leave_days("CL", start, end) == Decimal("2.0")

def test_calculate_leave_days_cl_single_weekday():
    start = date(2024, 10, 1) # Tuesday
    end = date(2024, 10, 1)
    assert rules.calculate_leave_days("CL", start, end) == Decimal("1.0")

def test_calculate_leave_days_cl_half_day_single_day():
    start = date(2024, 10, 1)
    end = date(2024, 10, 1)
    # Half day CL
    assert rules.calculate_leave_days("CL", start, end, half_day="first") == Decimal("0.5")

def test_calculate_leave_days_cl_half_day_on_sunday_raises():
    # CL on Sunday should not count, resulting in 0 days
    start = date(2026, 10, 25)
    end = date(2026, 10, 25)
    with pytest.raises(rules.RuleViolation):
        rules.calculate_leave_days("CL", start, end, half_day="first")

def test_calculate_leave_days_half_day_on_multi_day_range_raises():
    start = date(2024, 10, 1)
    end = date(2024, 10, 2)
    # Half day is only allowed for single day requests
    with pytest.raises(rules.RuleViolation):
        rules.calculate_leave_days("CL", start, end, half_day="first")

def test_calculate_leave_days_half_day_on_el_raises():
    # Half day is only allowed for CL
    start = date(2024, 10, 1)
    end = date(2024, 10, 1)
    with pytest.raises(rules.RuleViolation):
        rules.calculate_leave_days("EL", start, end, half_day="first")

def test_calculate_leave_days_bad_half_day_value_raises():
    start = date(2024, 10, 1)
    end = date(2024, 10, 1)
    with pytest.raises(rules.RuleViolation):
        rules.calculate_leave_days("CL", start, end, half_day="third")

def test_calculate_leave_days_cl_range_with_holiday_not_counted():
    # Assume 2024-10-02 is a holiday (Wednesday)
    holidays = frozenset([date(2024, 10, 2)])
    start = date(2024, 10, 1) # Tuesday
    end = date(2024, 10, 3) # Thursday
    # Tuesday (1), Wednesday (Holiday, 0), Thursday (1) = 2 days
    assert rules.calculate_leave_days("CL", start, end, holidays=holidays) == Decimal("2.0")

def test_calculate_leave_days_cl_range_with_weekend_and_holiday(weekend_dates):
    # Fri 2026-10-23 to Mon 2026-10-26
    # Assume 2026-10-23 (Fri) is a holiday
    holidays = frozenset([weekend_dates["fri"]])
    start = weekend_dates["fri"]
    end = weekend_dates["mon"]
    # Fri (Holiday, 0), Sat (Weekend, 0), Sun (Weekend, 0), Mon (1) = 1 day
    assert rules.calculate_leave_days("CL", start, end, holidays=holidays) == Decimal("1.0")

def test_calculate_leave_days_vl_counts_weekend(weekend_dates):
    assert rules.calculate_leave_days("VL", weekend_dates["fri"], weekend_dates["mon"]) == Decimal("4")

def test_calculate_leave_days_col_counts_weekend(weekend_dates):
    assert rules.calculate_leave_days("COL", weekend_dates["fri"], weekend_dates["mon"]) == Decimal("4")

def test_calculate_leave_days_scl_excludes_weekend(weekend_dates):
    assert rules.calculate_leave_days("SCL", weekend_dates["fri"], weekend_dates["mon"]) == Decimal("2")

def test_calculate_leave_days_rh_excludes_weekend(weekend_dates):
    assert rules.calculate_leave_days("RH", weekend_dates["fri"], weekend_dates["mon"]) == Decimal("2")

def test_calculate_leave_days_el_counts_holiday_inside_range(weekend_dates):
    holidays = frozenset([weekend_dates["sat"]])
    assert rules.calculate_leave_days("EL", weekend_dates["fri"], weekend_dates["mon"], holidays=holidays) == Decimal("4")

def test_calculate_leave_days_half_day_second_half_is_half(weekend_dates):
    assert rules.calculate_leave_days("CL", weekend_dates["mon"], weekend_dates["mon"], half_day="second") == Decimal("0.5")

def test_calculate_leave_days_half_day_on_holiday_raises(weekend_dates):
    holidays = frozenset([weekend_dates["mon"]])
    with pytest.raises(rules.RuleViolation):
        rules.calculate_leave_days("CL", weekend_dates["mon"], weekend_dates["mon"], half_day="first", holidays=holidays)

# --- Test Overlap ---

def test_check_overlap_disjoint_dates_false():
    existing = [(date(2024, 1, 1), date(2024, 1, 5), None)]
    new_start = date(2024, 1, 6)
    new_end = date(2024, 1, 10)
    assert rules.check_overlap(existing, new_start, new_end) is False

def test_check_overlap_touching_end_start_true():
    existing = [(date(2024, 1, 1), date(2024, 1, 5), None)]
    # new request starts on the last day of the existing one (ends are inclusive)
    assert rules.check_overlap(existing, date(2024, 1, 5), date(2024, 1, 10)) is True
    # new request ends on the first day of the existing one
    assert rules.check_overlap(existing, date(2023, 12, 28), date(2024, 1, 1)) is True

def test_check_overlap_full_overlap_true():
    existing = [(date(2024, 1, 1), date(2024, 1, 5), None)]
    new_start = date(2024, 1, 2)
    new_end = date(2024, 1, 4)
    assert rules.check_overlap(existing, new_start, new_end) is True

def test_check_overlap_empty_list_false():
    assert rules.check_overlap([], date(2024, 1, 1), date(2024, 1, 2)) is False

def test_check_overlap_half_vs_half_different_halves_no_overlap():
    date1 = date(2024, 1, 1)
    existing = [(date1, date1, "first")]
    new_start = date1
    new_end = date1
    # Exception: different halves on same date do NOT overlap
    assert rules.check_overlap(existing, new_start, new_end, new_half="second") is False

def test_check_overlap_half_vs_half_same_halves_overlap():
    date1 = date(2024, 1, 1)
    existing = [(date1, date1, "first")]
    new_start = date1
    new_end = date1
    # Same half on same date overlaps
    assert rules.check_overlap(existing, new_start, new_end, new_half="first") is True

def test_check_overlap_half_inside_multi_day_leave_overlap():
    date1 = date(2024, 1, 1)
    date2 = date(2024, 1, 5)
    existing = [(date1, date2, None)]
    new_start = date(2024, 1, 3)
    new_end = date(2024, 1, 3)
    # Half day inside a multi-day leave overlaps
    assert rules.check_overlap(existing, new_start, new_end, new_half="first") is True

def test_check_overlap_half_vs_full_day_same_date_overlap():
    date1 = date(2024, 1, 1)
    existing = [(date1, date1, None)] # Full day
    new_start = date1
    new_end = date1
    # Half day vs full day on same date overlaps
    assert rules.check_overlap(existing, new_start, new_end, new_half="first") is True

def test_check_overlap_second_half_vs_first_half_existing_no_overlap():
    day = date(2024, 1, 1)
    assert rules.check_overlap([(day, day, "second")], day, day, new_half="first") is False

def test_check_overlap_checks_every_existing_leave():
    existing = [(date(2024, 1, 1), date(2024, 1, 2), None), (date(2024, 2, 1), date(2024, 2, 5), None)]
    assert rules.check_overlap(existing, date(2024, 2, 3), date(2024, 2, 3)) is True

# --- Test Conversions and Balances ---

def test_convert_vl_to_el_standard():
    # 5 VL -> 2.5 EL
    assert rules.convert_vl_to_el(Decimal("5")) == Decimal("2.5")
    # 1 VL -> 0.5 EL
    assert rules.convert_vl_to_el(Decimal("1")) == Decimal("0.5")
    # 0 VL -> 0 EL
    assert rules.convert_vl_to_el(Decimal("0")) == Decimal("0")

def test_convert_vl_to_el_negative_raises():
    with pytest.raises(rules.RuleViolation):
        rules.convert_vl_to_el(Decimal("-1"))

def test_has_sufficient_balance_true():
    assert rules.has_sufficient_balance(Decimal("10"), Decimal("5")) is True

def test_has_sufficient_balance_false():
    assert rules.has_sufficient_balance(Decimal("5"), Decimal("10")) is False

def test_has_sufficient_balance_equal():
    assert rules.has_sufficient_balance(Decimal("10"), Decimal("10")) is True

def test_has_sufficient_balance_negative_balance_raises():
    with pytest.raises(rules.RuleViolation):
        rules.has_sufficient_balance(Decimal("-1"), Decimal("1"))

def test_has_sufficient_balance_negative_request_raises():
    with pytest.raises(rules.RuleViolation):
        rules.has_sufficient_balance(Decimal("10"), Decimal("-1"))

# --- Test Carry Forward ---

def test_carry_forward_lapse_categories():
    # CL, RH, SCL, VL lapse
    assert rules.carry_forward_amount("CL", Decimal("10")) == Decimal("0")
    assert rules.carry_forward_amount("RH", Decimal("5")) == Decimal("0")
    assert rules.carry_forward_amount("SCL", Decimal("20")) == Decimal("0")
    assert rules.carry_forward_amount("VL", Decimal("30")) == Decimal("0")

def test_carry_forward_carry_categories():
    # EL and COL carry forward
    assert rules.carry_forward_amount("EL", Decimal("30")) == Decimal("30")
    assert rules.carry_forward_amount("COL", Decimal("20")) == Decimal("20")

def test_carry_forward_unknown_category_raises():
    with pytest.raises(rules.RuleViolation):
        rules.carry_forward_amount("XX", Decimal("10"))
