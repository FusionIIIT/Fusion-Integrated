"""Focused regression tests for the Phase-2 ELM fixes."""
from decimal import Decimal

import pytest
from core.api.exceptions import ConflictError
from modules.leave.domain.state_machine import validate_transition
from modules.leave.domain.year_end import compute_year_end_transition


def test_resumption_review_is_a_terminal_state():
    validate_transition("resumption_submitted", "resumption_reviewed")
    with pytest.raises(ConflictError):
        validate_transition("resumption_reviewed", "approved")


def test_withdrawn_application_cannot_resume_normal_review():
    with pytest.raises(ConflictError):
        validate_transition("withdrawn", "approved")


def test_declined_substitute_does_not_reopen_a_withdrawn_application():
    with pytest.raises(ConflictError):
        validate_transition("withdrawn", "under_review")


def test_cancellation_request_can_be_rejected_without_closing_original_state():
    validate_transition("cancel_requested", "rejected")
    with pytest.raises(ConflictError):
        validate_transition("rejected", "approved")


def test_year_end_transition_is_decimal_safe():
    result = compute_year_end_transition(
        cl=Decimal("2.0"), rh=Decimal("1.0"), scl=Decimal("4.0"),
        el=Decimal("12.50"), vl=Decimal("30.0"), col=Decimal("3.0"),
        is_faculty=False,
    )
    assert result["carried_el"] >= Decimal("0.0")
    assert result["carried_col"] >= Decimal("0.0")
