"""Unit tests for leave state machine transitions."""
import pytest
from core.api.exceptions import ConflictError
from modules.leave.domain.state_machine import validate_transition


def test_valid_transitions():
    validate_transition("draft", "substitute_pending")
    validate_transition("substitute_pending", "under_review")
    validate_transition("under_review", "approved")
    validate_transition("approved", "cancel_requested")
    validate_transition("cancel_requested", "cancelled")
    validate_transition("approved", "resumption_submitted")
    validate_transition("resumption_submitted", "closed")


def test_invalid_transitions():
    with pytest.raises(ConflictError):
        validate_transition("draft", "approved")  # Cannot skip review

    with pytest.raises(ConflictError):
        validate_transition("closed", "approved")  # Terminal state
