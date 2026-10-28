import pytest

from modules.elm.domain import workflow
from modules.elm.domain.errors import ActorNotAllowed, InvalidTransition


def test_employee_can_withdraw_pending_request():
    transition = workflow.resolve(workflow.UNIT_HEAD_REVIEW, workflow.WITHDRAWN, "employee")
    assert transition.permission == "elm.request.withdraw"


def test_employee_cannot_approve_own_request():
    with pytest.raises(ActorNotAllowed):
        workflow.resolve(workflow.UNIT_HEAD_REVIEW, workflow.APPROVED, "employee")


def test_illegal_transition_is_rejected():
    with pytest.raises(InvalidTransition):
        workflow.resolve(workflow.WITHDRAWN, workflow.APPROVED, "authority")


def test_approved_leave_cannot_be_withdrawn():
    assert workflow.allowed_targets(workflow.APPROVED, "employee") == (
        workflow.CANCELLATION_PENDING,
        workflow.EXTENSION_PENDING,
        workflow.RESUMPTION_PENDING,
    )
