from datetime import date

import pytest

from modules.elm.domain.leave_rules import (
    LeavePeriod,
    LeaveRuleError,
    LeaveType,
    calculate_leave_days,
    convert_unused_vl_to_el,
    entitlement_for,
    periods_overlap,
)


def period(day, half=None):
    return LeavePeriod(day, day, LeaveType.CL, half)


def test_canonical_entitlements():
    assert entitlement_for(LeaveType.CL) == 8
    assert entitlement_for(LeaveType.RH) == 2
    assert entitlement_for(LeaveType.SCL) == 15
    assert entitlement_for(LeaveType.EL) == 30
    assert entitlement_for(LeaveType.COL) == 20
    assert entitlement_for(LeaveType.VL) is None


def test_faculty_el_is_policy_configured():
    assert entitlement_for(LeaveType.EL, is_faculty=True) is None


def test_rejects_end_before_start():
    with pytest.raises(LeaveRuleError):
        LeavePeriod(date(2026, 10, 12), date(2026, 10, 11), LeaveType.CL)


def test_half_day_cl_requests_for_different_halves_do_not_overlap():
    day = date(2026, 10, 12)
    assert not periods_overlap(period(day, "first"), period(day, "second"))


def test_half_day_cl_requests_for_same_half_overlap():
    day = date(2026, 10, 12)
    assert periods_overlap(period(day, "first"), period(day, "first"))


def test_full_day_cl_conflicts_with_half_day():
    day = date(2026, 10, 12)
    assert periods_overlap(period(day), period(day, "first"))


def test_half_day_only_allowed_for_cl():
    with pytest.raises(LeaveRuleError):
        LeavePeriod(
            date(2026, 10, 12),
            date(2026, 10, 12),
            LeaveType.RH,
            "first",
        )


def test_faculty_vacation_leave_entitlement_is_60_days():
    assert entitlement_for(LeaveType.VL, is_faculty=True) == 60


def test_vacation_leave_for_non_faculty_is_not_applicable():
    assert entitlement_for(LeaveType.VL, is_faculty=False) is None




def test_cl_excludes_weekends():
    from datetime import date

    assert calculate_leave_days(
        date(2026, 10, 10), date(2026, 10, 12), LeaveType.CL,
        working_weekdays={0, 1, 2, 3, 4},
    ) == 1


def test_el_counts_weekends():
    from datetime import date

    assert calculate_leave_days(
        date(2026, 10, 10), date(2026, 10, 12), LeaveType.EL,
        working_weekdays={0, 1, 2, 3, 4},
    ) == 3


def test_cl_excludes_closed_holidays():
    from datetime import date

    assert calculate_leave_days(
        date(2026, 10, 12),
        date(2026, 10, 13),
        LeaveType.CL,
        working_weekdays={0, 1, 2, 3, 4},
        closed_holidays={date(2026, 10, 13)},
    ) == 1



def test_half_day_cl_counts_as_half_day():
    assert calculate_leave_days(
        date(2026, 10, 12),
        date(2026, 10, 12),
        LeaveType.CL,
        working_weekdays={0, 1, 2, 3, 4},
        half_day="first",
    ) == 0.5


@pytest.mark.parametrize(
    ("unused_vl", "expected_el"),
    [
        (0, 0),
        (1, 0.5),
        (3, 1.5),
        (10, 5),
        (15, 7.5),
        (60, 30),
    ],
)
def test_vl_to_el_conversion_preserves_fractional_days(unused_vl, expected_el):
    from modules.elm.domain.leave_rules import convert_unused_vl_to_el

    assert convert_unused_vl_to_el(unused_vl) == expected_el


def test_vl_to_el_conversion_rejects_negative_balance():
    with pytest.raises(LeaveRuleError):
        convert_unused_vl_to_el(-1)
