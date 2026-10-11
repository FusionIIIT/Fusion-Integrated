
import pytest

from modules.elm.domain.state_machine import (
    APPROVED,
    DRAFT,
    PENDING,
    REJECTED,
    SUBMITTED,
    WITHDRAWN,
    InvalidTransition,
    allowed_actions,
    resolve,
)


def test_draft_can_be_submitted():
    transition = resolve(DRAFT, "submit")
    assert transition.target == SUBMITTED


def test_pending_request_can_be_approved_or_rejected():
    assert resolve(PENDING, "approve").target == APPROVED
    assert resolve(PENDING, "reject").target == REJECTED


def test_submitted_request_can_be_withdrawn():
    assert resolve(SUBMITTED, "withdraw").target == WITHDRAWN


def test_cannot_approve_draft():
    with pytest.raises(InvalidTransition):
        resolve(DRAFT, "approve")


def test_cannot_reject_already_approved_request():
    with pytest.raises(InvalidTransition):
        resolve(APPROVED, "reject")


def test_allowed_actions_for_pending_request():
    assert allowed_actions(PENDING) == ("approve", "reject")
