"""State machine table tests for SPACS module."""

import pytest

from modules.spacs.domain.errors import InvalidTransitionError
from modules.spacs.domain.state_machine import (
    is_application_transition_legal,
    is_award_transition_legal,
    resolve_application_transition,
    resolve_award_transition,
)


def test_valid_application_lifecycle():
    """Verify standard happy-path transitions for an application."""
    t1 = resolve_application_transition("draft", "submit", "student")
    assert t1.target == "submitted"

    t2 = resolve_application_transition("submitted", "open_verification", "spacs_assistant")
    assert t2.target == "under_verification"

    t3 = resolve_application_transition("under_verification", "mark_verified", "spacs_assistant")
    assert t3.target == "verified"

    t4 = resolve_application_transition("verified", "open_decision", "spacs_convener")
    assert t4.target == "under_convener_review"

    t5 = resolve_application_transition("under_convener_review", "approve", "spacs_convener")
    assert t5.target == "approved"


def test_invalid_application_transitions():
    """Verify illegal transitions are rejected."""
    with pytest.raises(InvalidTransitionError):
        resolve_application_transition("draft", "approve", "spacs_convener")

    with pytest.raises(InvalidTransitionError):
        resolve_application_transition("approved", "submit", "student")

    with pytest.raises(InvalidTransitionError):
        resolve_application_transition("draft", "submit", "spacs_assistant")

    with pytest.raises(InvalidTransitionError):
        resolve_award_transition("open", "prepare_pool", "student")

    with pytest.raises(InvalidTransitionError):
        resolve_award_transition("published", "submit", "student")


def test_award_cycle_lifecycle():
    """Verify award cycle lifecycle transitions."""
    t1 = resolve_award_transition("open", "prepare_pool", "spacs_convener")
    assert t1.target == "pool_prepared"

    t2 = resolve_award_transition("pool_prepared", "begin_evaluation", "award_evaluation_committee")
    assert t2.target == "under_committee_evaluation"

    t3 = resolve_award_transition(
        "under_committee_evaluation", "record_committee_result", "award_evaluation_committee"
    )
    assert t3.target == "committee_result_recorded"


def test_is_transition_legal():
    """Verify boolean transition helper checks."""
    assert is_application_transition_legal("draft", "submitted")
    assert not is_application_transition_legal("draft", "approved")
    assert is_award_transition_legal("open", "pool_prepared")
    assert not is_award_transition_legal("open", "published")
