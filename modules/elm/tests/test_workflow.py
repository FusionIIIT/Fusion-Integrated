"""Tests for the pure ELM new-leave state machine."""

import pytest

from modules.elm.domain.leave_policy import LeaveCategory
from modules.elm.domain.workflow import (
    PENDING_STATES,
    WorkflowTransitionError,
    transition,
)
from modules.elm.domain.workflow import (
    LeaveWorkflowAction as Action,
)
from modules.elm.domain.workflow import (
    LeaveWorkflowState as State,
)
from modules.elm.models import LEAVE_APPLICATION_STATUS_CHOICES


def next_state(state, action, category="EL", **kwargs):
    return transition(state, action, category=category, **kwargs)


def test_domain_states_match_application_model_choices():
    model_states = {value for value, _label in LEAVE_APPLICATION_STATUS_CHOICES}
    domain_states = {state.value for state in State}

    assert domain_states == model_states


@pytest.mark.parametrize("category", list(LeaveCategory))
def test_submit_without_substitute_routes_to_unit_head_for_non_director(category):
    result = next_state(
        State.DRAFT,
        Action.SUBMIT,
        category=category,
    )

    assert result == State.AWAITING_UNIT_HEAD_REVIEW


def test_submission_with_required_substitute_waits_for_consent():
    result = next_state(
        State.DRAFT,
        Action.SUBMIT,
        substitute_required=True,
    )

    assert result == State.AWAITING_SUBSTITUTE_RESPONSE


def test_director_without_substitute_uses_self_sanction_route():
    result = next_state(
        State.DRAFT,
        Action.SUBMIT,
        applicant_is_director=True,
    )

    assert result == State.AWAITING_DIRECTOR_SELF_SANCTION


def test_accepted_substitute_routes_director_to_self_sanction():
    result = next_state(
        State.AWAITING_SUBSTITUTE_RESPONSE,
        Action.ACCEPT_SUBSTITUTE,
        applicant_is_director=True,
    )

    assert result == State.AWAITING_DIRECTOR_SELF_SANCTION


def test_accepted_substitute_routes_other_applicant_to_unit_head():
    result = next_state(
        State.AWAITING_SUBSTITUTE_RESPONSE,
        Action.ACCEPT_SUBSTITUTE,
    )

    assert result == State.AWAITING_UNIT_HEAD_REVIEW


def test_declined_substitute_requires_applicant_action():
    result = next_state(
        State.AWAITING_SUBSTITUTE_RESPONSE,
        Action.DECLINE_SUBSTITUTE,
    )

    assert result == State.APPLICANT_ACTION_REQUIRED


def test_replacement_nomination_returns_to_substitute_response():
    result = next_state(
        State.APPLICANT_ACTION_REQUIRED,
        Action.NOMINATE_REPLACEMENT,
    )

    assert result == State.AWAITING_SUBSTITUTE_RESPONSE


@pytest.mark.parametrize("category", [LeaveCategory.CL, LeaveCategory.RH])
def test_unit_head_is_final_authority_for_cl_and_rh(category):
    assert (
        next_state(
            State.AWAITING_UNIT_HEAD_REVIEW,
            Action.UNIT_HEAD_APPROVE,
            category=category,
        )
        == State.APPROVED
    )

    assert (
        next_state(
            State.AWAITING_UNIT_HEAD_REVIEW,
            Action.UNIT_HEAD_REJECT,
            category=category,
        )
        == State.REJECTED
    )


@pytest.mark.parametrize(
    "action",
    [Action.UNIT_HEAD_RECOMMEND, Action.UNIT_HEAD_NOT_RECOMMEND],
)
def test_higher_sanction_unit_head_outcome_routes_to_establishment_when_configured(
    action,
):
    result = next_state(
        State.AWAITING_UNIT_HEAD_REVIEW,
        action,
        category=LeaveCategory.EL,
        establishment_configured=True,
    )

    assert result == State.AWAITING_ESTABLISHMENT_ROUTING


@pytest.mark.parametrize(
    "action",
    [Action.UNIT_HEAD_RECOMMEND, Action.UNIT_HEAD_NOT_RECOMMEND],
)
def test_higher_sanction_unit_head_outcome_can_bypass_establishment(action):
    result = next_state(
        State.AWAITING_UNIT_HEAD_REVIEW,
        action,
        category=LeaveCategory.VL,
        establishment_configured=False,
    )

    assert result == State.AWAITING_FINAL_SANCTION_DECISION


def test_not_recommended_is_not_final_rejection():
    result = next_state(
        State.AWAITING_UNIT_HEAD_REVIEW,
        Action.UNIT_HEAD_NOT_RECOMMEND,
        category=LeaveCategory.SCL,
    )

    assert result == State.AWAITING_FINAL_SANCTION_DECISION


def test_establishment_routes_to_final_sanction():
    result = next_state(
        State.AWAITING_ESTABLISHMENT_ROUTING,
        Action.ROUTE_TO_FINAL_SANCTION,
        category=LeaveCategory.COL,
    )

    assert result == State.AWAITING_FINAL_SANCTION_DECISION


def test_final_sanction_can_approve_or_reject():
    assert (
        next_state(
            State.AWAITING_FINAL_SANCTION_DECISION,
            Action.FINAL_APPROVE,
            category=LeaveCategory.EL,
        )
        == State.APPROVED
    )

    assert (
        next_state(
            State.AWAITING_FINAL_SANCTION_DECISION,
            Action.FINAL_REJECT,
            category=LeaveCategory.EL,
        )
        == State.REJECTED
    )


def test_director_can_approve_or_reject_own_leave_on_self_sanction_route():
    assert (
        next_state(
            State.AWAITING_DIRECTOR_SELF_SANCTION,
            Action.DIRECTOR_APPROVE,
            category=LeaveCategory.EL,
        )
        == State.APPROVED
    )

    assert (
        next_state(
            State.AWAITING_DIRECTOR_SELF_SANCTION,
            Action.DIRECTOR_REJECT,
            category=LeaveCategory.EL,
        )
        == State.REJECTED
    )


@pytest.mark.parametrize("state", list(PENDING_STATES))
def test_pending_requests_can_be_withdrawn(state):
    assert next_state(state, Action.WITHDRAW) == State.WITHDRAWN


@pytest.mark.parametrize(
    "state",
    [State.APPROVED, State.REJECTED, State.WITHDRAWN, State.CANCELLED],
)
def test_terminal_requests_cannot_be_withdrawn_again(state):
    with pytest.raises(WorkflowTransitionError):
        next_state(state, Action.WITHDRAW)


def test_unit_head_cannot_finally_reject_higher_sanction_leave():
    with pytest.raises(WorkflowTransitionError):
        next_state(
            State.AWAITING_UNIT_HEAD_REVIEW,
            Action.UNIT_HEAD_REJECT,
            category=LeaveCategory.EL,
        )


def test_unit_head_cannot_use_higher_sanction_recommendation_for_cl():
    with pytest.raises(WorkflowTransitionError):
        next_state(
            State.AWAITING_UNIT_HEAD_REVIEW,
            Action.UNIT_HEAD_NOT_RECOMMEND,
            category=LeaveCategory.CL,
        )


def test_invalid_state_is_rejected():
    with pytest.raises(WorkflowTransitionError):
        next_state("unknown", Action.SUBMIT)


def test_invalid_action_is_rejected():
    with pytest.raises(WorkflowTransitionError):
        next_state(State.DRAFT, "approve_anyway")
