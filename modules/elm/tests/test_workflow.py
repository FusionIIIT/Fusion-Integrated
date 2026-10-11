import pytest

from modules.elm.domain.workflow import (
    InvalidTransition,
    LeaveStatus,
    can_cancel_approved_leave,
    transition,
)


def test_valid_transition():
    assert transition(
        LeaveStatus.DRAFT, LeaveStatus.PENDING_SUBSTITUTE
    ) == LeaveStatus.PENDING_SUBSTITUTE


def test_cannot_edit_submitted_request_in_place():
    with pytest.raises(InvalidTransition):
        transition(LeaveStatus.PENDING_UNIT_HEAD, LeaveStatus.DRAFT)


def test_terminal_rejection_cannot_be_reopened():
    with pytest.raises(InvalidTransition):
        transition(LeaveStatus.REJECTED, LeaveStatus.PENDING_SANCTION)


def test_cancellation_only_before_start():
    from datetime import date

    assert can_cancel_approved_leave(
        LeaveStatus.APPROVED, date(2026, 10, 20), date(2026, 10, 19)
    )
    assert not can_cancel_approved_leave(
        LeaveStatus.APPROVED, date(2026, 10, 20), date(2026, 10, 20)
    )
