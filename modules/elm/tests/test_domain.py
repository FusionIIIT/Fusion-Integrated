"""Pure Python Domain Unit Tests for ELM.

Runs in milliseconds without a database or network connection.
Verifies all core calculation rules and workflow state machines.
"""
from datetime import date

from modules.elm.domain.calculations import (
    calculate_leave_days,
    calculate_vl_to_el_conversion,
    check_date_overlap,
)
from modules.elm.domain.entities import LeaveCategory, LeaveStatus
from modules.elm.domain.state_machine import LeaveStateMachine


def test_half_day_cl_calculation():
    """BR-EL-010: Half-day CL consumes exactly 0.5 days."""
    days = calculate_leave_days(
        category=LeaveCategory.CL,
        start_date=date(2026, 10, 15),
        end_date=date(2026, 10, 15),
        is_half_day=True,
        half_day_period="first_half",
    )
    assert days == 0.5


def test_continuous_counting_for_earned_leave():
    """BR-EL-011: EL includes intervening weekends and holidays continuously."""
    # From Friday to Monday = 4 calendar days (Friday, Saturday, Sunday, Monday)
    start = date(2026, 10, 16)  # Friday
    end = date(2026, 10, 19)    # Monday
    days = calculate_leave_days(category=LeaveCategory.EL, start_date=start, end_date=end)
    assert days == 4.0


def test_working_days_counting_for_casual_leave():
    """BR-EL-011: CL excludes intervening weekends."""
    start = date(2026, 10, 16)  # Friday
    end = date(2026, 10, 19)    # Monday
    days = calculate_leave_days(category=LeaveCategory.CL, start_date=start, end_date=end)
    # Friday and Monday are working days; Saturday and Sunday are excluded -> 2 days
    assert days == 2.0


def test_faculty_vl_to_el_conversion():
    """BR-EL-007: All unused Faculty VL converts to EL at 2:1."""
    assert calculate_vl_to_el_conversion(30.0) == 15.0
    assert calculate_vl_to_el_conversion(15.0) == 7.5
    assert calculate_vl_to_el_conversion(0.0) == 0.0


def test_half_day_cl_non_overlap():
    """BR-EL-012: First-half and second-half CL on same date do not overlap."""
    d = date(2026, 10, 20)
    overlap = check_date_overlap(
        start1=d, end1=d, is_half1=True, period1="first_half",
        start2=d, end2=d, is_half2=True, period2="second_half",
    )
    assert overlap is False


def test_date_overlap_detection():
    """Regular dates overlap correctly."""
    overlap = check_date_overlap(
        start1=date(2026, 10, 10), end1=date(2026, 10, 15), is_half1=False, period1=None,
        start2=date(2026, 10, 14), end2=date(2026, 10, 20), is_half2=False, period2=None,
    )
    assert overlap is True


def test_state_machine_cl_progression():
    """CW-EL-01: CL approval directly at Unit Head."""
    # Submission without substitute
    st = LeaveStateMachine.submit_application(requires_substitute=False, is_director=False)
    assert st == LeaveStatus.AWAITING_UNIT_HEAD

    # Unit Head Approves CL
    res = LeaveStateMachine.unit_head_review("CL", "approve")
    assert res.success is True
    assert res.new_status == LeaveStatus.APPROVED


def test_state_machine_higher_sanction_progression():
    """CW-EL-01: Higher sanction leave progression."""
    # Unit Head recommends
    res = LeaveStateMachine.unit_head_review("EL", "recommend", has_establishment_step=True)
    assert res.success is True
    assert res.new_status == LeaveStatus.AWAITING_ESTABLISHMENT

    # Establishment routes
    res = LeaveStateMachine.establishment_route()
    assert res.success is True
    assert res.new_status == LeaveStatus.AWAITING_FINAL_SANCTION

    # Final sanction approves
    res = LeaveStateMachine.final_sanction(approved=True)
    assert res.success is True
    assert res.new_status == LeaveStatus.APPROVED


def test_immediate_withdrawal():
    """CW-EL-01, BR-EL-022: Immediate withdrawal on pending requests."""
    res = LeaveStateMachine.withdraw_pending(LeaveStatus.AWAITING_UNIT_HEAD)
    assert res.success is True
    assert res.new_status == LeaveStatus.WITHDRAWN

    # Cannot withdraw approved leave
    res_invalid = LeaveStateMachine.withdraw_pending(LeaveStatus.APPROVED)
    assert res_invalid.success is False


def test_extension_state_machine_includes_decline_replacement_and_routing():
    """CW-EL-03: Extension consent and hierarchy states remain distinct."""
    declined = LeaveStateMachine.process_substitute_response(
        LeaveStatus.EXTENSION_PENDING_SUBSTITUTE, accepted=False, is_director=False
    )
    assert declined.new_status == LeaveStatus.EXTENSION_APPLICANT_ACTION_REQUIRED

    replaced = LeaveStateMachine.replace_extension_substitute(declined.new_status)
    assert replaced.success is True
    assert replaced.new_status == LeaveStatus.EXTENSION_PENDING_SUBSTITUTE

    accepted = LeaveStateMachine.process_substitute_response(
        replaced.new_status, accepted=True, is_director=False
    )
    assert accepted.new_status == LeaveStatus.EXTENSION_PENDING_UNIT_HEAD

    recommended = LeaveStateMachine.extension_unit_head_review(
        accepted.new_status, decision="recommend", has_establishment_step=True
    )
    assert recommended.new_status == LeaveStatus.EXTENSION_PENDING_ESTABLISHMENT

    routed = LeaveStateMachine.extension_establishment_route(recommended.new_status)
    assert routed.new_status == LeaveStatus.EXTENSION_PENDING_FINAL

    withdrawn = LeaveStateMachine.withdraw_pending(routed.new_status)
    assert withdrawn.success is True
    assert withdrawn.new_status == LeaveStatus.WITHDRAWN
