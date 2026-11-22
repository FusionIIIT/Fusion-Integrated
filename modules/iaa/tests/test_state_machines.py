"""State machine tests: pure Python, no database."""

import pytest

from modules.iaa.domain.state_machine import (
    ANOMALY_TRANSITIONS,
    AUDIT_TRANSITIONS,
    EXPENSE_TRANSITIONS,
    TA_TRANSITIONS,
    InvalidStateTransitionError,
    transition_anomaly,
    transition_audit_observation,
    transition_expense_request,
    transition_ta_claim,
)


def test_expense_valid_transitions():
    assert transition_expense_request("draft", "submit", "basic_user") == "submitted"
    assert transition_expense_request("submitted", "raise_query", "finance_staff") == "query_raised"
    assert (
        transition_expense_request("query_raised", "respond_query", "basic_user")
        == "query_responded"
    )
    assert (
        transition_expense_request("query_responded", "validate", "finance_staff")
        == "finance_validated"
    )
    assert (
        transition_expense_request("submitted", "validate", "finance_staff") == "finance_validated"
    )
    assert (
        transition_expense_request("finance_validated", "approve_final", "approving_authority")
        == "approved"
    )
    assert (
        transition_expense_request("finance_validated", "reject", "approving_authority")
        == "rejected"
    )
    assert (
        transition_expense_request("finance_validated", "timeout_escalate", "system") == "escalated"
    )
    assert transition_expense_request("approved", "record", "finance_staff") == "recorded"


def test_expense_invalid_transition_raises():
    with pytest.raises(InvalidStateTransitionError):
        transition_expense_request("draft", "approve_final", "approving_authority")
    with pytest.raises(InvalidStateTransitionError):
        transition_expense_request("recorded", "submit", "basic_user")
    with pytest.raises(InvalidStateTransitionError):
        transition_expense_request("submitted", "submit", "basic_user")


def test_ta_valid_transitions():
    assert transition_ta_claim("not_submitted", "submit", "basic_user") == "submitted"
    assert transition_ta_claim("submitted", "verify_standard", "finance_staff") == "verified"
    assert (
        transition_ta_claim("submitted", "verify_high_value", "finance_staff") == "approval_pending"
    )
    assert (
        transition_ta_claim("approval_pending", "approve_final", "approving_authority")
        == "approved"
    )
    assert transition_ta_claim("approval_pending", "reject", "approving_authority") == "rejected"
    assert transition_ta_claim("verified", "record", "finance_staff") == "recorded"
    assert transition_ta_claim("approved", "record", "finance_staff") == "recorded"


def test_ta_invalid_transitions():
    with pytest.raises(InvalidStateTransitionError):
        transition_ta_claim("not_submitted", "record", "finance_staff")
    with pytest.raises(InvalidStateTransitionError):
        transition_ta_claim("recorded", "verify_standard", "finance_staff")


def test_anomaly_transitions():
    assert transition_anomaly("none", "flag_manual", "finance_or_auditor") == "open"
    assert transition_anomaly("none", "flag_automatic", "system") == "open"
    assert transition_anomaly("open", "resolve", "resolver") == "resolved"
    assert transition_anomaly("open", "escalate", "resolver") == "escalated"
    assert transition_anomaly("escalated", "resolve", "resolver") == "resolved"
    with pytest.raises(InvalidStateTransitionError):
        transition_anomaly("resolved", "escalate", "resolver")


def test_audit_observation_transitions():
    assert transition_audit_observation("none", "create", "auditor") == "open"
    assert transition_audit_observation("open", "respond", "basic_user") == "responded"
    assert transition_audit_observation("responded", "close", "auditor") == "closed"
    assert transition_audit_observation("responded", "reject_response", "auditor") == "open"
    with pytest.raises(InvalidStateTransitionError):
        transition_audit_observation("closed", "respond", "basic_user")


def test_all_declared_transitions_succeed():
    for (state, event, role), target in EXPENSE_TRANSITIONS.items():
        assert transition_expense_request(state, event, role) == target
    for (state, event, role), target in TA_TRANSITIONS.items():
        assert transition_ta_claim(state, event, role) == target
    for (state, event, role), target in ANOMALY_TRANSITIONS.items():
        assert transition_anomaly(state, event, role) == target
    for (state, event, role), target in AUDIT_TRANSITIONS.items():
        assert transition_audit_observation(state, event, role) == target
