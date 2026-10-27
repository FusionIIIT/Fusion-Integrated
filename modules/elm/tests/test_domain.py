"""Domain unit tests for ELM state machine and transitions.

Per the Module Authoring Guide, domain tests have zero database and zero Django dependencies.
"""
import pytest

from modules.elm.domain.entities import LeaveCategory, LeaveStatus
from modules.elm.domain.errors import InvalidTransition
from modules.elm.domain.state_machine import (
    TERMINAL_STATES,
    TRANSITIONS,
    validate_step_decision,
    validate_transition,
)


def test_submitted_can_transition_to_recommended():
    validate_transition("submitted", "recommended")


def test_submitted_can_transition_to_approved():
    validate_transition("submitted", "approved")


def test_submitted_can_transition_to_rejected():
    validate_transition("submitted", "rejected")


def test_submitted_can_be_withdrawn():
    validate_transition("submitted", "withdrawn")


def test_recommended_can_be_approved():
    validate_transition("recommended", "approved")


def test_not_recommended_can_be_approved_by_higher_authority():
    validate_transition("not_recommended", "approved")


def test_approved_can_be_cancelled():
    validate_transition("approved", "cancelled")


def test_cannot_transition_from_rejected_to_approved():
    with pytest.raises(InvalidTransition):
        validate_transition("rejected", "approved")


def test_cannot_transition_from_withdrawn_to_approved():
    with pytest.raises(InvalidTransition):
        validate_transition("withdrawn", "approved")


def test_recommendation_step_accepts_only_recommendation_decisions():
    validate_step_decision("recommendation", "recommended")
    validate_step_decision("recommendation", "not_recommended")
    with pytest.raises(InvalidTransition):
        validate_step_decision("recommendation", "approved")


def test_final_step_accepts_only_final_decisions():
    validate_step_decision("final_decision", "approved")
    validate_step_decision("final_decision", "rejected")
    with pytest.raises(InvalidTransition):
        validate_step_decision("final_decision", "recommended")


def test_cannot_transition_from_cancelled_to_submitted():
    with pytest.raises(InvalidTransition):
        validate_transition("cancelled", "submitted")
