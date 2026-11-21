from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.elm.domain.rules import (
    ENTITLEMENTS,
    calculate_vl_to_el_conversion,
    can_substitute,
    count_leave_days,
    intervals_overlap,
    validate_station_leave,
)


@pytest.mark.parametrize("category", ["", "UNKNOWN", "cl", "SL", None])
def test_invalid_leave_categories_are_rejected(category):
    with pytest.raises(ValueError, match="Invalid leave category"):
        count_leave_days(category, date(2026, 1, 1), date(2026, 1, 1))


@pytest.mark.parametrize("category", ENTITLEMENTS)
def test_reversed_dates_are_rejected_for_all_categories(category):
    with pytest.raises(ValueError, match="Start date must be before end date"):
        count_leave_days(category, date(2026, 1, 2), date(2026, 1, 1))


@pytest.mark.parametrize("category", ["EL", "VL", "COL"])
def test_continuous_leave_includes_every_calendar_day(category):
    start, end = date(2026, 1, 2), date(2026, 1, 6)
    assert count_leave_days(category, start, end, closed_dates={start, end}) == Decimal("5")


@pytest.mark.parametrize("category", ["CL", "SCL", "RH"])
def test_working_day_leave_excludes_only_dates_in_closed_set(category):
    start, end = date(2026, 1, 2), date(2026, 1, 6)
    assert count_leave_days(category, start, end, closed_dates={start, end}) == Decimal("3")


@pytest.mark.parametrize("half_day", ["first", "second"])
def test_half_day_cl_for_closed_date_still_counts_half(half_day):
    d = date(2026, 1, 2)
    assert count_leave_days("CL", d, d, half_day=half_day, closed_dates={d}) == Decimal("0.5")


@pytest.mark.parametrize("half_day", [None, "", "FIRST", "morning", "third"])
def test_invalid_or_missing_half_day_uses_full_day(half_day):
    d = date(2026, 1, 2)
    assert count_leave_days("CL", d, d, half_day=half_day) == Decimal("1")


@pytest.mark.parametrize("category", ["RH", "SCL", "EL", "VL", "COL"])
def test_half_day_marker_does_not_reduce_non_cl_leave(category):
    d = date(2026, 1, 2)
    assert count_leave_days(category, d, d, half_day="first") == Decimal("1")


@pytest.mark.parametrize("unutilized,current,cap,credited,forfeited,new", [
    ("0", "10", "300", "0", "0", "10"),
    ("20", "100", "300", "10", "0", "110"),
    ("15", "100", "300", "7.5", "0", "107.5"),
    ("20", "295", "300", "5", "10", "300"),
    ("20", "300", "300", "0", "20", "300"),
    ("20", "310", "300", "0", "20", "310"),
    ("1", "0", "300", "0.5", "0", "0.5"),
])
def test_vl_conversion_respects_ratio_cap_and_forfeiture(unutilized, current, cap, credited, forfeited, new):
    result = calculate_vl_to_el_conversion(Decimal(unutilized), Decimal(current), Decimal(cap))
    assert result == (Decimal(credited), Decimal(forfeited), Decimal(new))


@pytest.mark.parametrize("destination,contact", [(None, None), ("", "123"), ("  ", "123"), ("X", None), ("X", " ")])
def test_station_leave_requires_both_nonblank_fields(destination, contact):
    assert validate_station_leave(True, destination, contact) is False


@pytest.mark.parametrize("destination,contact", [(None, None), ("", ""), ("  ", " ")])
def test_non_station_leave_does_not_validate_optional_details(destination, contact):
    assert validate_station_leave(False, destination, contact) is True


@pytest.mark.parametrize("left,right,expected", [(1, 2, True), (2, 1, True), (1, 1, False), (0, 0, False)])
def test_substitute_must_be_different_person(left, right, expected):
    assert can_substitute(left, right) is expected


@pytest.mark.parametrize("gap", [0, 1])
def test_touching_date_ranges_overlap_but_one_day_gap_does_not(gap):
    start = date(2026, 4, 1)
    left_end = start + timedelta(days=2)
    right_start = left_end + timedelta(days=gap)
    result = intervals_overlap(start, left_end, None, right_start, right_start + timedelta(days=1), None)
    assert result is (gap == 0)


@pytest.mark.parametrize("half_a,half_b,expected", [
    ("first", "second", False), ("second", "first", False),
    ("first", "first", True), ("second", "second", True),
    (None, "first", True), ("first", None, True),
])
def test_same_day_half_day_overlap_exception(half_a, half_b, expected):
    d = date(2026, 4, 1)
    assert intervals_overlap(d, d, half_a, d, d, half_b) is expected
