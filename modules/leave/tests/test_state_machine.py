"""Unit tests for leave state machine transitions."""

import pytest

from modules.leave.domain import (
    RESUMPTION_REVIEWED_EARLY,
    RESUMPTION_REVIEWED_LATE,
    RESUMPTION_REVIEWED_NORMAL,
    InvalidStateTransitionError,
    validate_transition,
)


def test_valid_transitions():
    validate_transition("draft", "substitute_pending")
    validate_transition("substitute_pending", "under_review")
    validate_transition("substitute_pending", "applicant_action_required")
    validate_transition("applicant_action_required", "substitute_pending")
    validate_transition("extension_requested", "withdrawn")
    validate_transition("under_review", "approved")
    validate_transition("approved", "cancel_requested")
    validate_transition("cancel_requested", "cancelled")
    validate_transition("approved", "resumption_submitted")
    validate_transition("resumption_submitted", RESUMPTION_REVIEWED_NORMAL)
    validate_transition("resumption_submitted", RESUMPTION_REVIEWED_EARLY)
    validate_transition("resumption_submitted", RESUMPTION_REVIEWED_LATE)


def test_invalid_transitions():
    with pytest.raises(InvalidStateTransitionError):
        validate_transition("draft", "approved")  # Cannot skip review

    with pytest.raises(InvalidStateTransitionError):
        validate_transition("closed", "approved")  # Terminal state

    with pytest.raises(InvalidStateTransitionError):
        validate_transition("withdrawn", "under_review")  # A stale response cannot revive it
