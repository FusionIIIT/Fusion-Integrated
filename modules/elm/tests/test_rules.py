"""Unit tests for pure-Python ELM business rules (BR-EL-001 through BR-EL-020)."""
from datetime import date
from decimal import Decimal
import pytest

from modules.elm.domain.entities import LeaveCategory
from modules.elm.domain.errors import (
    InsufficientLeaveBalance,
    InvalidLeaveDatesError,
    InvalidSubstituteError,
    OverlappingLeaveError,
    PolicyValidationError,
)
from modules.elm.domain.rules import (
    calculate_duration_days,
    convert_vl_to_el,
    resolve_approval_chain,
    validate_balance_available,
    validate_no_overlap,
    validate_substitute,
)


def test_half_day_cl_counts_as_half_day():
    """BR-EL-010: Half-day CL consumes 0.5 CL day."""
    d = date(2026, 11, 2)  # Monday
    days = calculate_duration_days(d, d, LeaveCategory.CL, is_half_day=True)
    assert days == Decimal("0.5")


def test_half_day_forbidden_for_non_cl():
    """Half-day leave only allowed for CL."""
    d = date(2026, 11, 2)
    with pytest.raises(PolicyValidationError):
        calculate_duration_days(d, d, LeaveCategory.EL, is_half_day=True)


def test_continuous_counting_includes_weekends_and_holidays():
    """BR-EL-011: For EL, COL, VL, intervening weekends and holidays count as leave days."""
    start = date(2026, 11, 6)   # Friday
    end = date(2026, 11, 9)     # Monday (Fri, Sat, Sun, Mon = 4 calendar days)
    holidays = {date(2026, 11, 6)}

    # EL counts 4 days
    days = calculate_duration_days(start, end, LeaveCategory.EL, holiday_calendar_dates=holidays)
    assert days == Decimal("4")


def test_non_continuous_counting_excludes_weekends_and_holidays():
    """BR-EL-011: For CL, SCL, RH, intervening weekends and holidays do not count."""
    start = date(2026, 11, 6)   # Friday
    end = date(2026, 11, 9)     # Monday
    # Sat 7 and Sun 8 are skipped. If Fri 6 is holiday, only Mon 9 counts (1 day).
    holidays = {date(2026, 11, 6)}

    days = calculate_duration_days(start, end, LeaveCategory.CL, holiday_calendar_dates=holidays)
    assert days == Decimal("1")


def test_inverted_dates_raise_error():
    """Start date after end date raises InvalidLeaveDatesError."""
    with pytest.raises(InvalidLeaveDatesError):
        calculate_duration_days(date(2026, 11, 10), date(2026, 11, 5), LeaveCategory.CL)


def test_balance_validation():
    """Insufficient balance raises InsufficientLeaveBalance."""
    validate_balance_available(Decimal("5.0"), Decimal("3.0"))  # Passes
    with pytest.raises(InsufficientLeaveBalance):
        validate_balance_available(Decimal("2.0"), Decimal("3.0"))


def test_vl_to_el_conversion():
    """BR-EL-007: 2 VL : 1 EL conversion including fractional."""
    assert convert_vl_to_el(Decimal("10.0")) == Decimal("5.00")
    assert convert_vl_to_el(Decimal("7.0")) == Decimal("3.50")
    assert convert_vl_to_el(Decimal("0.0")) == Decimal("0.0")


def test_non_overlapping_validation():
    """BR-EL-012: Overlapping active leave raises OverlappingLeaveError."""
    existing = [
        {"id": 1, "leave_start": date(2026, 11, 5), "leave_end": date(2026, 11, 8), "status": "approved"}
    ]
    # Overlaps
    with pytest.raises(OverlappingLeaveError):
        validate_no_overlap(date(2026, 11, 7), date(2026, 11, 10), False, "", existing)

    # Disjoint (passes)
    validate_no_overlap(date(2026, 11, 10), date(2026, 11, 12), False, "", existing)


def test_morning_and_afternoon_cl_exception():
    """BR-EL-012: Morning and afternoon CL on the same date are permissible non-overlap."""
    d = date(2026, 11, 5)
    existing = [
        {"id": 1, "leave_start": d, "leave_end": d, "is_half_day": True, "half_day": "morning", "status": "approved"}
    ]
    # Afternoon on same date passes
    validate_no_overlap(d, d, is_half_day=True, half_day="afternoon", existing_leaves=existing)

    # Morning on same date fails
    with pytest.raises(OverlappingLeaveError):
        validate_no_overlap(d, d, is_half_day=True, half_day="morning", existing_leaves=existing)


def test_substitute_validation():
    """BR-EL-014: Cannot nominate self, cannot have overlapping leave."""
    with pytest.raises(InvalidSubstituteError):
        validate_substitute(10, 10, date(2026, 11, 1), date(2026, 11, 2))

    sub_leaves = [
        {"id": 2, "leave_start": date(2026, 11, 1), "leave_end": date(2026, 11, 5), "status": "approved"}
    ]
    with pytest.raises(InvalidSubstituteError):
        validate_substitute(10, 20, date(2026, 11, 3), date(2026, 11, 4), substitute_leaves=sub_leaves)


def test_director_self_sanction_routing():
    """BR-EL-020: Director applicant has single self-sanction step."""
    steps = resolve_approval_chain(LeaveCategory.EL, "director", 1, unit_head_id=2)
    assert len(steps) == 1
    assert steps[0]["assigned_role"] == "director"
    assert steps[0]["step_type"] == "final_decision"


def test_cl_rh_unit_head_final_routing():
    """BR-EL-016: CL/RH has Unit Head as final authority."""
    steps = resolve_approval_chain(LeaveCategory.CL, "faculty", 10, unit_head_id=2)
    assert len(steps) == 1
    assert steps[0]["assigned_role"] == "unit_head"
    assert steps[0]["step_type"] == "final_decision"


def test_higher_sanction_routing():
    """BR-EL-017 & 018: SCL/EL/COL/VL has Unit Head recommendation then higher authority."""
    steps = resolve_approval_chain(
        LeaveCategory.EL,
        "faculty",
        10,
        unit_head_id=2,
        higher_authorities=[("dean", 3), ("director", 1)],
    )
    assert len(steps) == 3
    assert steps[0]["step_type"] == "recommendation"
    assert steps[1]["step_type"] == "recommendation"
    assert steps[2]["step_type"] == "final_decision"
