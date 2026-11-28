import datetime
from decimal import Decimal

import pytest

from modules.leave.domain import errors, rules
from modules.leave.domain.counting import count_leave_days
from modules.leave.domain.state_machine import (
    TERMINAL_STATES,
    LeaveEvent,
    LeaveState,
    transition,
)


def test_count_leave_days_working_days():
    # 2026-01-05 (Monday) to 2026-01-09 (Friday) = 5 working days
    mon = datetime.date(2026, 1, 5)
    fri = datetime.date(2026, 1, 9)
    days = count_leave_days("CL", mon, fri, "none", set())
    assert days == Decimal("5.0")


def test_count_leave_days_skips_weekends_for_cl():
    # 2026-01-09 (Friday) to 2026-01-12 (Monday) = 2 working days (Sat & Sun excluded)
    fri = datetime.date(2026, 1, 9)
    mon = datetime.date(2026, 1, 12)
    days = count_leave_days("CL", fri, mon, "none", set())
    assert days == Decimal("2.0")


def test_count_leave_days_continuous_counts_calendar_days():
    # EL counts all calendar days including weekends
    fri = datetime.date(2026, 1, 9)
    mon = datetime.date(2026, 1, 12)
    days = count_leave_days("EL", fri, mon, "none", set())
    assert days == Decimal("4.0")


def test_count_leave_days_half_day_cl():
    mon = datetime.date(2026, 1, 5)
    days = count_leave_days("CL", mon, mon, "first_half", set())
    assert days == Decimal("0.5")


def test_count_leave_days_half_day_invalid_for_multi_day():
    mon = datetime.date(2026, 1, 5)
    tue = datetime.date(2026, 1, 6)
    with pytest.raises(errors.LeavePolicyViolationError):
        count_leave_days("CL", mon, tue, "first_half", set())


def test_count_leave_days_half_day_invalid_for_el():
    mon = datetime.date(2026, 1, 5)
    with pytest.raises(errors.LeavePolicyViolationError):
        count_leave_days("EL", mon, mon, "first_half", set())


def test_validate_category_eligibility():
    # Staff cannot take VL
    with pytest.raises(errors.IneligibleCategoryError):
        rules.validate_category_eligibility("VL", is_faculty=False)
    # Faculty can take VL
    rules.validate_category_eligibility("VL", is_faculty=True)


def test_validate_substitute():
    with pytest.raises(errors.IneligibleSubstituteError):
        rules.validate_substitute(applicant_id=10, substitute_id=10)
    rules.validate_substitute(applicant_id=10, substitute_id=20)


def test_validate_restricted_holiday():
    rh_date = datetime.date(2026, 1, 14)
    # Valid RH
    rules.validate_restricted_holiday(rh_date, rh_date, [rh_date])

    # RH cannot span multiple days
    with pytest.raises(errors.LeavePolicyViolationError):
        rules.validate_restricted_holiday(rh_date, datetime.date(2026, 1, 15), [rh_date])

    # Date not in calendar RH list
    with pytest.raises(errors.LeavePolicyViolationError):
        rules.validate_restricted_holiday(datetime.date(2026, 1, 16), datetime.date(2026, 1, 16), [rh_date])


def test_validate_vacation_period():
    v_start = datetime.date(2026, 5, 15)
    v_end = datetime.date(2026, 7, 15)
    vacations = [(v_start, v_end)]

    # Inside vacation
    rules.validate_vacation_period(datetime.date(2026, 6, 1), datetime.date(2026, 6, 10), vacations)

    # Outside vacation raises error
    with pytest.raises(errors.LeavePolicyViolationError):
        rules.validate_vacation_period(datetime.date(2026, 5, 1), datetime.date(2026, 5, 20), vacations)


def test_convert_vl_to_el():
    # 30 days of unavailed VL with 2:1 ratio = 15 days EL
    el = rules.convert_vl_to_el(Decimal("30.0"), Decimal("2.0"))
    assert el == Decimal("15.0")

    # 15 days of VL with 2:1 ratio = 7.5 days EL
    el_half = rules.convert_vl_to_el(Decimal("15.0"), Decimal("2.0"))
    assert el_half == Decimal("7.5")


def test_state_machine_valid_transitions():
    assert transition(LeaveState.DRAFT, LeaveEvent.SUBMIT) == LeaveState.PENDING_REVIEW
    assert (
        transition(LeaveState.SUBMITTED_PENDING_SUBSTITUTE, LeaveEvent.SUBSTITUTE_ACCEPT)
        == LeaveState.PENDING_REVIEW
    )
    assert (
        transition(LeaveState.SUBMITTED_PENDING_SUBSTITUTE, LeaveEvent.SUBSTITUTE_DECLINE)
        == LeaveState.SUBSTITUTE_DECLINED
    )
    assert transition(LeaveState.PENDING_REVIEW, LeaveEvent.UH_APPROVE) == LeaveState.APPROVED
    assert transition(LeaveState.PENDING_REVIEW, LeaveEvent.UH_RECOMMEND) == LeaveState.PENDING_ROUTING
    assert transition(LeaveState.PENDING_ROUTING, LeaveEvent.ROUTE) == LeaveState.PENDING_SANCTION
    assert transition(LeaveState.PENDING_SANCTION, LeaveEvent.SANCTION_APPROVE) == LeaveState.APPROVED
    assert transition(LeaveState.APPROVED, LeaveEvent.SUBMIT_RESUMPTION) == LeaveState.RESUMPTION_PENDING
    assert transition(LeaveState.RESUMPTION_PENDING, LeaveEvent.VERIFY_RESUMPTION) == LeaveState.CLOSED


def test_state_machine_invalid_transition():
    with pytest.raises(errors.InvalidLeaveTransitionError):
        transition(LeaveState.DRAFT, LeaveEvent.SANCTION_APPROVE)


def test_terminal_states_no_transitions():
    events = [getattr(LeaveEvent, attr) for attr in dir(LeaveEvent) if not attr.startswith("_")]
    for term in TERMINAL_STATES:
        for ev in events:
            with pytest.raises(errors.InvalidLeaveTransitionError):
                transition(term, ev)
