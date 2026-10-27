# Task: add missing day-counting tests to modules/leave/tests/test_rules.py (complete file output)

Mutation testing showed the tests only cover day counting for EL and CL. Keep ALL existing tests unchanged and add exactly these
tests in the "Test Day Counting" section (use the existing `weekend_dates` fixture: fri 2026-10-23, sat, sun, mon 2026-10-26):

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

Output the COMPLETE file only. No explanations, no placeholders, no TODOs.
