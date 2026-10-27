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
    validate_transition("cancel_requested", "rejected")
    validate_transition("approved", "resumption_submitted")
    validate_transition("resumption_submitted", "resumption_reviewed")


def test_invalid_transitions():
    with pytest.raises(ConflictError):
        validate_transition("draft", "approved")
    with pytest.raises(ConflictError):
        validate_transition("resumption_reviewed", "approved")
