"""Leave domain state machine tests — pure Python, no database."""
import pytest

from modules.leave.domain import state_machine as sm


def test_requester_can_cancel_pending():
    t = sm.resolve(sm.PENDING, sm.CANCELLED, sm.REQUESTER)
    assert t.to == sm.CANCELLED


def test_approver_can_approve_pending():
    t = sm.resolve(sm.PENDING, sm.APPROVED, sm.APPROVER)
    assert t.to == sm.APPROVED


def test_approver_can_reject_pending_with_reason():
    t = sm.resolve(sm.PENDING, sm.REJECTED, sm.APPROVER)
    assert "has_reason" in t.guards


def test_requester_cannot_approve():
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.PENDING, sm.APPROVED, sm.REQUESTER)


def test_approver_cannot_cancel():
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.PENDING, sm.CANCELLED, sm.APPROVER)


def test_cannot_transition_from_rejected():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.REJECTED, sm.APPROVED, sm.APPROVER)


def test_approved_can_be_cancelled_by_requester():
    t = sm.resolve(sm.APPROVED, sm.CANCELLED, sm.REQUESTER)
    assert t.to == sm.CANCELLED


def test_approved_can_be_revoked_by_approver():
    t = sm.resolve(sm.APPROVED, sm.REVOKED, sm.APPROVER)
    assert "has_reason" in t.guards
