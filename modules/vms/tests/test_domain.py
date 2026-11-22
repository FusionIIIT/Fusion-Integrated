"""VMS Pure Domain Tests.
Tests pure Python business rules, state machine invariants, and calculations.
Runs in milliseconds with NO database.
"""

from datetime import UTC, datetime, timedelta

import pytest

from modules.vms.domain.rules import (
    calculate_walk_in_duration,
    check_overstay,
    validate_blacklist_match,
    validate_same_day_pass,
    validate_zone_access,
)
from modules.vms.domain.state_machine import (
    TERMINAL_STATES,
    InvalidStateTransitionError,
    TransitionTrigger,
    VisitState,
    validate_transition,
)


# --- 1. State Machine Tests ---
def test_valid_state_transitions():
    """Verifies that all declared transitions succeed and produce expected states."""
    assert (
        validate_transition(VisitState.REQUESTED.value, TransitionTrigger.HOST_APPROVE.value)
        == VisitState.APPROVED.value
    )
    assert (
        validate_transition(VisitState.REQUESTED.value, TransitionTrigger.HOST_REJECT.value)
        == VisitState.REJECTED.value
    )
    assert (
        validate_transition(VisitState.REQUESTED.value, TransitionTrigger.VISITOR_CANCEL.value)
        == VisitState.CANCELLED.value
    )
    assert (
        validate_transition(VisitState.REQUESTED.value, TransitionTrigger.TIMEOUT.value)
        == VisitState.EXPIRED.value
    )
    assert (
        validate_transition(VisitState.APPROVED.value, TransitionTrigger.GATE_CHECK_IN.value)
        == VisitState.ON_SITE.value
    )
    assert (
        validate_transition(VisitState.ON_SITE.value, TransitionTrigger.GATE_CHECK_OUT.value)
        == VisitState.COMPLETED.value
    )


def test_terminal_states_cannot_transition():
    """Rule BR-023: Terminal states have no exit transitions."""
    for terminal in TERMINAL_STATES:
        for trigger in TransitionTrigger:
            with pytest.raises(InvalidStateTransitionError):
                validate_transition(terminal, trigger.value)


def test_invalid_trigger_raises():
    """An undeclared transition raises InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(VisitState.REQUESTED.value, TransitionTrigger.GATE_CHECK_OUT.value)


# --- 2. Blacklist Rules (BR-001 & BR-004) ---
def test_blacklist_exact_match_rule_br_001():
    blacklist = [
        {
            "id_number_hash": "HASH_123",
            "phone": "9999999999",
            "full_name": "Bad Actor",
            "severity": "critical",
            "is_active": True,
            "reason": "Banned",
        }
    ]
    res = validate_blacklist_match("HASH_123", "8888888888", "Good Person", blacklist)
    assert res.is_blacklisted is True
    assert res.matched_rule == "BR-001"


def test_blacklist_quorum_match_rule_br_004():
    blacklist = [
        {
            "id_number_hash": "OTHER_HASH",
            "phone": "9999999999",
            "full_name": "Sneaky Actor",
            "severity": "warning",
            "is_active": True,
            "reason": "Watchlist",
        }
    ]
    res = validate_blacklist_match("HASH_XYZ", "9999999999", "Sneaky Actor", blacklist)
    assert res.is_blacklisted is True
    assert res.matched_rule == "BR-004"


def test_blacklist_clean_visitor():
    blacklist = [
        {
            "id_number_hash": "HASH_123",
            "phone": "9999999999",
            "full_name": "Bad Actor",
            "severity": "critical",
            "is_active": True,
        }
    ]
    res = validate_blacklist_match("CLEAN_HASH", "1111111111", "Clean Guest", blacklist)
    assert res.is_blacklisted is False


# --- 3. Duplicate Pass Prevention (BR-017 & BR-020) ---
def test_same_day_duplicate_pass_refusal():
    existing_dates = ["2026-11-22", "2026-11-20"]
    res = validate_same_day_pass("2026-11-22", existing_dates)
    assert res.allowed is False
    assert res.rule_id == "BR-020"

    res_allowed = validate_same_day_pass("2026-11-23", existing_dates)
    assert res_allowed.allowed is True


# --- 4. Walk-in Pass Duration (BR-032) ---
def test_walk_in_duration_strictly_four_hours():
    now = datetime(2026, 11, 22, 10, 0, 0, tzinfo=UTC)
    v_from, v_to = calculate_walk_in_duration(now)
    assert v_from == now
    assert v_to == now + timedelta(hours=4)


# --- 5. Zone Access Rules (BR-041) ---
def test_zone_access_authorization():
    allowed_zones = ["MAIN_GATE", "ADMIN_BLOCK", "HOSTEL_ZONE"]
    assert validate_zone_access(allowed_zones, "ADMIN_BLOCK").allowed is True
    assert validate_zone_access(allowed_zones, "admin_block").allowed is True

    denied = validate_zone_access(allowed_zones, "SERVER_ROOM")
    assert denied.allowed is False
    assert denied.rule_id == "BR-041"


# --- 6. Overstay Rules (BR-045) ---
def test_overstay_detection():
    now = datetime(2026, 11, 22, 14, 0, 0, tzinfo=UTC)
    valid_to_past = datetime(2026, 11, 22, 13, 59, 0, tzinfo=UTC)
    valid_to_future = datetime(2026, 11, 22, 15, 0, 0, tzinfo=UTC)

    assert check_overstay(valid_to_past, now) is True
    assert check_overstay(valid_to_future, now) is False
