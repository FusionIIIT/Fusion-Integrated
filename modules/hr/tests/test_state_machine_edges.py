"""Boundary cases for HR workflow state machines."""

import pytest

from modules.hr.domain import state_machine as sm


@pytest.mark.parametrize("length", [1, 2])
def test_leave_route_accepts_one_or_two_authorities(length):
    assert sm.supports_leave_route_length(length)


@pytest.mark.parametrize("length", [0, 3])
def test_leave_route_rejects_unsupported_authority_count(length):
    assert not sm.supports_leave_route_length(length)


@pytest.mark.parametrize(
    ("state", "action", "step", "length", "transition"),
    [
        (sm.LEAVE_PENDING, "reject", 0, 1, (sm.LEAVE_REJECTED, 0)),
        (sm.LEAVE_PENDING_NEXT, "reject", 1, 2, (sm.LEAVE_REJECTED, 1)),
    ],
)
def test_leave_rejection_is_allowed_at_current_authority(state, action, step, length, transition):
    result = sm.decide_leave(state, action=action, authority_step=step, route_length=length)
    assert (result.state, result.authority_step) == transition


@pytest.mark.parametrize(
    ("state", "action", "step", "length", "error_action"),
    [
        ("closed", "approve", 0, 1, "approve"),
        (sm.LEAVE_PENDING, "forward", 0, 0, "route_invalid"),
        (sm.LEAVE_PENDING, "forward", 0, 3, "route_invalid"),
        (sm.LEAVE_PENDING_NEXT, "approve", 2, 2, "route_invalid"),
        (sm.LEAVE_PENDING, "forward", 0, 1, "no_next_authority"),
        (sm.LEAVE_PENDING_NEXT, "forward", 1, 2, "forwarding_already_used"),
        (sm.LEAVE_PENDING, "approve", 0, 2, "approval_must_follow_route"),
    ],
)
def test_leave_rejects_invalid_workflow_steps(state, action, step, length, error_action):
    with pytest.raises(sm.InvalidTransition) as error:
        sm.decide_leave(state, action=action, authority_step=step, route_length=length)
    assert error.value.action == error_action


def test_claim_verification_requires_pending_verification_state():
    with pytest.raises(sm.InvalidTransition) as error:
        sm.verify_claim(sm.APPROVED, verified=True, has_route=True)
    assert error.value.action == "verify"


def test_claim_verification_can_remain_pending_after_failed_verification():
    result = sm.verify_claim(sm.PENDING_VERIFICATION, verified=False, has_route=False)
    assert (result.state, result.authority_step) == (sm.PENDING_VERIFICATION, 0)


def test_successful_claim_verification_requires_configured_route():
    with pytest.raises(sm.InvalidTransition) as error:
        sm.verify_claim(sm.PENDING_VERIFICATION, verified=True, has_route=False)
    assert error.value.action == "route_not_configured"


def test_successful_claim_verification_moves_to_first_authority():
    result = sm.verify_claim(sm.PENDING_VERIFICATION, verified=True, has_route=True)
    assert (result.state, result.authority_step) == (sm.PENDING_AUTHORITY, 0)


@pytest.mark.parametrize(
    ("state", "action", "step", "length", "expected"),
    [
        (sm.PENDING_AUTHORITY, "forward", 0, 2, (sm.PENDING_NEXT_AUTHORITY, 1)),
        (sm.PENDING_NEXT_AUTHORITY, "approve", 1, 2, (sm.APPROVED, 1)),
        (sm.PENDING_AUTHORITY, "reject", 0, 1, (sm.REJECTED, 0)),
    ],
)
def test_claim_decision_routes_forward_and_resolves(state, action, step, length, expected):
    result = sm.decide_claim(state, action=action, authority_step=step, route_length=length)
    assert (result.state, result.authority_step) == expected


@pytest.mark.parametrize(
    ("state", "action", "step", "length", "error_action"),
    [
        (sm.PENDING_VERIFICATION, "approve", 0, 1, "approve"),
        (sm.PENDING_AUTHORITY, "approve", 0, 0, "route_invalid"),
        (sm.PENDING_AUTHORITY, "approve", 1, 1, "route_invalid"),
        (sm.PENDING_AUTHORITY, "forward", 0, 1, "no_next_authority"),
        (sm.PENDING_AUTHORITY, "approve", 0, 2, "approval_must_follow_route"),
        (sm.PENDING_AUTHORITY, "withdraw", 0, 1, "withdraw"),
    ],
)
def test_claim_decision_rejects_invalid_steps(state, action, step, length, error_action):
    with pytest.raises(sm.InvalidTransition) as error:
        sm.decide_claim(state, action=action, authority_step=step, route_length=length)
    assert error.value.action == error_action


def test_appraisal_assignment_only_accepts_submitted_state():
    sm.verify_appraisal_state(sm.SUBMITTED)
    with pytest.raises(sm.InvalidTransition) as error:
        sm.verify_appraisal_state(sm.PENDING_REVIEW)
    assert error.value.action == "assign_reviewers"


@pytest.mark.parametrize(
    ("state", "action", "index", "count", "expected"),
    [
        (sm.PENDING_REVIEW, "forward", 0, 2, (sm.APPRAISAL_PENDING_NEXT, 1)),
        (sm.APPRAISAL_PENDING_NEXT, "finalize", 1, 2, (sm.CLOSED, 1)),
    ],
)
def test_appraisal_review_advances_in_configured_order(state, action, index, count, expected):
    result = sm.review_appraisal(state, action=action, current_index=index, reviewer_count=count)
    assert (result.state, result.authority_step) == expected


@pytest.mark.parametrize(
    ("state", "action", "index", "count", "error_action"),
    [
        (sm.SUBMITTED, "finalize", 0, 1, "finalize"),
        (sm.PENDING_REVIEW, "finalize", 0, 0, "reviewers_invalid"),
        (sm.PENDING_REVIEW, "finalize", 2, 2, "reviewers_invalid"),
        (sm.PENDING_REVIEW, "forward", 0, 1, "no_next_reviewer"),
        (sm.PENDING_REVIEW, "finalize", 0, 2, "finalization_must_follow_route"),
        (sm.PENDING_REVIEW, "reject", 0, 1, "reject"),
    ],
)
def test_appraisal_review_rejects_invalid_steps(state, action, index, count, error_action):
    with pytest.raises(sm.InvalidTransition) as error:
        sm.review_appraisal(state, action=action, current_index=index, reviewer_count=count)
    assert error.value.action == error_action
