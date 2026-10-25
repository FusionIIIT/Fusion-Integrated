"""Unit tests for ELM pure Python domain rules and state machine."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.entities import LeaveInterval
from modules.elm.domain.errors import (
    IllegalStateTransitionError,
    IneligibleCategoryError,
    InsufficientLeaveBalanceError,
    InvalidLeaveDateError,
    InvalidSubstituteError,
    StationLeaveValidationError,
)
from modules.elm.domain.policy import (
    calculate_leave_days,
    is_overlapping,
    validate_leave_application,
)
from modules.elm.domain.state_machine import ElmStateMachine


def test_calculate_leave_days_cl_skips_weekends():
    # 2026-10-23 is Friday, 24 Sat, 25 Sun, 26 Mon -> only Fri & Mon = 2 days
    fri = date(2026, 10, 23)
    mon = date(2026, 10, 26)
    days = calculate_leave_days("CL", fri, mon)
    assert days == Decimal("2.0")


def test_calculate_leave_days_cl_skips_holidays():
    fri = date(2026, 10, 23)
    mon = date(2026, 10, 26)
    holidays = {mon}
    days = calculate_leave_days("CL", fri, mon, holidays=holidays)
    assert days == Decimal("1.0")


def test_calculate_leave_days_half_day_cl():
    fri = date(2026, 10, 23)
    days = calculate_leave_days("CL", fri, fri, half_day="first_half")
    assert days == Decimal("0.5")


def test_calculate_leave_days_half_day_invalid_on_multi_day():
    fri = date(2026, 10, 23)
    mon = date(2026, 10, 26)
    with pytest.raises(InvalidLeaveDateError, match="single day"):
        calculate_leave_days("CL", fri, mon, half_day="first_half")


def test_calculate_leave_days_half_day_invalid_on_non_cl():
    fri = date(2026, 10, 23)
    with pytest.raises(InvalidLeaveDateError, match="Casual Leave"):
        calculate_leave_days("EL", fri, fri, half_day="first_half")


def test_calculate_leave_days_continuous_counting_for_el():
    # Fri to Mon is 4 calendar days
    fri = date(2026, 10, 23)
    mon = date(2026, 10, 26)
    days = calculate_leave_days("EL", fri, mon)
    assert days == Decimal("4.0")


def test_calculate_leave_days_continuous_counting_for_col_and_vl():
    d1 = date(2026, 11, 1)
    d5 = date(2026, 11, 5)
    assert calculate_leave_days("COL", d1, d5) == Decimal("5.0")
    assert calculate_leave_days("VL", d1, d5) == Decimal("5.0")


def test_calculate_leave_days_invalid_start_after_end():
    d1 = date(2026, 11, 5)
    d2 = date(2026, 11, 1)
    with pytest.raises(InvalidLeaveDateError, match="after end date"):
        calculate_leave_days("CL", d1, d2)


def test_is_overlapping_basic():
    existing = [LeaveInterval(start_date=date(2026, 10, 10), end_date=date(2026, 10, 15))]
    assert is_overlapping(date(2026, 10, 12), date(2026, 10, 14), "none", existing)
    assert is_overlapping(date(2026, 10, 5), date(2026, 10, 10), "none", existing)
    assert not is_overlapping(date(2026, 10, 16), date(2026, 10, 20), "none", existing)


def test_is_overlapping_complementary_half_days_on_same_date():
    target = date(2026, 10, 10)
    existing = [LeaveInterval(start_date=target, end_date=target, half_day="first_half")]
    # Second half on the same day must NOT be considered overlapping
    assert not is_overlapping(target, target, "second_half", existing)
    # First half on the same day DOES overlap
    assert is_overlapping(target, target, "first_half", existing)
    # Full day on the same day DOES overlap
    assert is_overlapping(target, target, "none", existing)


def test_validate_leave_application_faculty_vl_rule():
    d = date(2026, 10, 12)
    # Staff cannot apply for VL
    with pytest.raises(IneligibleCategoryError, match="restricted to faculty"):
        validate_leave_application(
            category_code="VL",
            start_date=d,
            end_date=d,
            half_day="none",
            is_faculty=False,
            current_balance=Decimal("60.0"),
            pending_days=Decimal("0.0"),
            station_leave=False,
            station_address="",
            emergency_contact="",
            substitute_id=None,
            applicant_id=1001,
        )


def test_validate_leave_application_balance_check():
    d = date(2026, 10, 12)
    with pytest.raises(InsufficientLeaveBalanceError, match="Insufficient"):
        validate_leave_application(
            category_code="CL",
            start_date=d,
            end_date=d,
            half_day="none",
            is_faculty=True,
            current_balance=Decimal("0.0"),
            pending_days=Decimal("0.0"),
            station_leave=False,
            station_address="",
            emergency_contact="",
            substitute_id=None,
            applicant_id=1001,
        )


def test_validate_leave_application_self_substitute():
    d = date(2026, 10, 12)
    with pytest.raises(InvalidSubstituteError, match="cannot nominate themselves"):
        validate_leave_application(
            category_code="CL",
            start_date=d,
            end_date=d,
            half_day="none",
            is_faculty=True,
            current_balance=Decimal("5.0"),
            pending_days=Decimal("0.0"),
            station_leave=False,
            station_address="",
            emergency_contact="",
            substitute_id=1001,
            applicant_id=1001,
        )


def test_validate_leave_application_station_leave_fields():
    d = date(2026, 10, 12)
    with pytest.raises(StationLeaveValidationError):
        validate_leave_application(
            category_code="CL",
            start_date=d,
            end_date=d,
            half_day="none",
            is_faculty=True,
            current_balance=Decimal("5.0"),
            pending_days=Decimal("0.0"),
            station_leave=True,
            station_address="",
            emergency_contact="12345",
            substitute_id=None,
            applicant_id=1001,
        )


def test_state_machine_cl_unit_head_decision():
    # Unit head can directly approve or reject CL
    status, rec = ElmStateMachine.transition_unit_head("CL", "submitted", "approve")
    assert status == "approved"
    assert rec == "recommended"

    status, rec = ElmStateMachine.transition_unit_head("CL", "submitted", "reject")
    assert status == "rejected"
    assert rec == "not_recommended"


def test_state_machine_el_unit_head_routes_to_sanction():
    # For EL, Unit Head recommendation moves request to pending_sanction
    status, rec = ElmStateMachine.transition_unit_head("EL", "submitted", "recommend")
    assert status == "pending_sanction"
    assert rec == "recommended"

    # Even not_recommend moves to pending_sanction (not a final rejection)
    status, rec = ElmStateMachine.transition_unit_head("EL", "submitted", "not_recommend")
    assert status == "pending_sanction"
    assert rec == "not_recommended"


def test_state_machine_sanctioning_authority():
    status = ElmStateMachine.transition_sanctioning_authority("EL", "pending_sanction", "approve")
    assert status == "approved"

    status = ElmStateMachine.transition_sanctioning_authority("EL", "pending_sanction", "reject")
    assert status == "rejected"


def test_state_machine_substitute_consent():
    status, sub_status = ElmStateMachine.transition_substitute("pending_substitute", "accept")
    assert status == "submitted"
    assert sub_status == "accepted"

    status, sub_status = ElmStateMachine.transition_substitute("pending_substitute", "decline")
    assert status == "pending_substitute"
    assert sub_status == "declined"


def test_state_machine_withdraw():
    assert ElmStateMachine.transition_withdraw("submitted") == "withdrawn"
    assert ElmStateMachine.transition_withdraw("pending_sanction") == "withdrawn"
    with pytest.raises(IllegalStateTransitionError):
        ElmStateMachine.transition_withdraw("approved")
