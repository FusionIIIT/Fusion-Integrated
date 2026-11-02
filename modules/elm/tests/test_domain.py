"""Pure Python Domain Unit Tests for ELM.

Runs in milliseconds without a database or network connection.
Verifies all core calculation rules and workflow state machines.
"""
from datetime import date
import pytest

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


def test_half_day_cl_different_dates_raises_error():
    """BR-EL-010: Half-day CL across multiple dates is invalid."""
    with pytest.raises(ValueError):
        calculate_leave_days(
            category=LeaveCategory.CL,
            start_date=date(2026, 10, 15),
            end_date=date(2026, 10, 16),
            is_half_day=True,
        )


def test_continuous_counting_for_earned_leave():
    """BR-EL-011: EL includes intervening weekends and holidays continuously."""
    # Friday 2026-10-16 to Monday 2026-10-19 = 4 calendar days
    start = date(2026, 10, 16)
    end = date(2026, 10, 19)
    days = calculate_leave_days(category=LeaveCategory.EL, start_date=start, end_date=end)
    assert days == 4.0


def test_working_days_counting_for_casual_leave():
    """BR-EL-011: CL excludes intervening weekends and closed holidays."""
    # Friday 2026-10-16 to Monday 2026-10-19:
    # Friday (work), Sat (weekend), Sun (weekend), Monday (work) -> 2 working days
    start = date(2026, 10, 16)
    end = date(2026, 10, 19)
    days = calculate_leave_days(category=LeaveCategory.CL, start_date=start, end_date=end)
    assert days == 2.0


def test_working_days_with_closed_holiday():
    """BR-EL-011: Closed holidays are excluded from CL calculation."""
    start = date(2026, 10, 14)  # Wednesday
    end = date(2026, 10, 16)    # Friday (3 days)
    # Thursday is a closed holiday
    closed_holiday = date(2026, 10, 15)
    days = calculate_leave_days(
        category=LeaveCategory.CL,
        start_date=start,
        end_date=end,
        closed_holidays={closed_holiday},
    )
    assert days == 2.0


def test_vl_to_el_conversion():
    """BR-EL-007: 2 unused Vacation Leaves convert to 1 Earned Leave."""
    assert calculate_vl_to_el_conversion(30.0) == 15.0
    assert calculate_vl_to_el_conversion(15.0) == 7.5
    assert calculate_vl_to_el_conversion(0.0) == 0.0


def test_check_date_overlap():
    assert check_date_overlap(date(2026, 10, 1), date(2026, 10, 10), date(2026, 10, 5), date(2026, 10, 15)) is True
    assert check_date_overlap(date(2026, 10, 1), date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 10)) is False


def test_state_machine_submission_with_substitute():
    """Draft -> Awaiting Substitute."""
    status = LeaveStateMachine.submit_application(requires_substitute=True)
    assert status == LeaveStatus.AWAITING_SUBSTITUTE


def test_state_machine_submission_without_substitute():
    """Draft -> Awaiting Unit Head."""
    status = LeaveStateMachine.submit_application(requires_substitute=False)
    assert status == LeaveStatus.AWAITING_UNIT_HEAD


def test_state_machine_substitute_accepts():
    """Awaiting Substitute -> Awaiting Unit Head."""
    res = LeaveStateMachine.process_substitute_response(
        LeaveStatus.AWAITING_SUBSTITUTE, accepted=True
    )
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.AWAITING_UNIT_HEAD


def test_state_machine_substitute_declines():
    """Awaiting Substitute -> Substitute Declined."""
    res = LeaveStateMachine.process_substitute_response(
        LeaveStatus.AWAITING_SUBSTITUTE, accepted=False
    )
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.SUBSTITUTE_DECLINED


def test_state_machine_unit_head_recommends():
    """Awaiting Unit Head -> Awaiting Sanction."""
    res = LeaveStateMachine.process_unit_head_review(
        LeaveStatus.AWAITING_UNIT_HEAD, recommended=True
    )
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.AWAITING_SANCTION


def test_state_machine_unit_head_rejects():
    """Awaiting Unit Head -> Rejected."""
    res = LeaveStateMachine.process_unit_head_review(
        LeaveStatus.AWAITING_UNIT_HEAD, recommended=False
    )
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.REJECTED


def test_state_machine_sanction_approves():
    """Awaiting Sanction -> Approved."""
    res = LeaveStateMachine.process_sanction_decision(
        LeaveStatus.AWAITING_SANCTION, approved=True
    )
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.APPROVED


def test_state_machine_sanction_rejects():
    """Awaiting Sanction -> Rejected."""
    res = LeaveStateMachine.process_sanction_decision(
        LeaveStatus.AWAITING_SANCTION, approved=False
    )
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.REJECTED


def test_state_machine_withdraw_pending():
    """Pending requests can be withdrawn."""
    res = LeaveStateMachine.withdraw(LeaveStatus.AWAITING_UNIT_HEAD)
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.WITHDRAWN


def test_state_machine_cannot_withdraw_approved():
    """Approved requests cannot be withdrawn."""
    res = LeaveStateMachine.withdraw(LeaveStatus.APPROVED)
    assert res.is_valid is False


def test_pre_start_cancellation():
    """Approved leaves can be cancelled on or before start date."""
    res = LeaveStateMachine.cancel_approved_leave(
        current_status=LeaveStatus.APPROVED,
        start_date=date(2026, 11, 1),
        today=date(2026, 10, 26),
    )
    assert res.is_valid is True
    assert res.next_status == LeaveStatus.CANCELLED


def test_post_start_cancellation_forbidden():
    """Cancellation after leave commences is rejected."""
    res = LeaveStateMachine.cancel_approved_leave(
        current_status=LeaveStatus.APPROVED,
        start_date=date(2026, 10, 20),
        today=date(2026, 10, 26),
    )
    assert res.is_valid is False
