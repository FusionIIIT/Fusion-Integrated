"""Unit tests for pure Python domain logic in the IWD module."""

from decimal import Decimal

import pytest

from modules.iwd.domain.assignment import select_best_engineer
from modules.iwd.domain.cost_bands import (
    BAND_HIGH,
    BAND_LOW,
    BAND_MID,
    LOW_COST_THRESHOLD,
    MID_COST_MAX_THRESHOLD,
    classify_band,
)
from modules.iwd.domain.state_machine import (
    InvalidStateTransitionError,
    IWDState,
    RoleSeparationViolationError,
    get_next_state,
)


def test_classify_band_low():
    """Verify band low classification below 25,000 threshold."""
    assert classify_band(0) == BAND_LOW
    assert classify_band(24999.99) == BAND_LOW
    assert classify_band("24999") == BAND_LOW


def test_classify_band_mid():
    """Verify band mid classification between 25,000 and 250,000."""
    assert classify_band(25000) == BAND_MID
    assert classify_band("100000") == BAND_MID
    assert classify_band(Decimal("250000.00")) == BAND_MID


def test_classify_band_high():
    """Verify band high classification exceeding 250,000."""
    assert classify_band(250000.01) == BAND_HIGH
    assert classify_band(500000) == BAND_HIGH


def test_band_thresholds_constants():
    """Verify band threshold boundary constants."""
    assert Decimal("25000.00") == LOW_COST_THRESHOLD
    assert Decimal("250000.00") == MID_COST_MAX_THRESHOLD


def test_select_best_engineer_lowest_workload():
    """Select engineer with lowest active ticket count."""
    engineers = [1, 2, 3]
    workload = {1: 5, 2: 2, 3: 4}
    assert select_best_engineer(engineers, workload) == 2


def test_select_best_engineer_tie_breaker():
    """Select lowest ID engineer in case of tie workload."""
    engineers = [5, 2]
    workload = {5: 2, 2: 2}
    assert select_best_engineer(engineers, workload) == 2


def test_select_best_engineer_empty():
    """Return None when no engineers are available."""
    assert select_best_engineer([], {}) is None


def test_state_machine_valid_transitions():
    """Verify declarative valid transitions across lifecycle."""
    s1 = get_next_state(IWDState.SUBMITTED, "assign", "system")
    assert s1 == IWDState.ASSIGNED

    s2 = get_next_state(IWDState.ASSIGNED, "assess", "iwd_engineer")
    assert s2 == IWDState.ASSESSED

    s3 = get_next_state(IWDState.ASSESSED, "submit_low", "iwd_engineer")
    assert s3 == IWDState.LOW_COST_REVIEW_PENDING

    s4 = get_next_state(IWDState.LOW_COST_REVIEW_PENDING, "approve", "iwd_engineer")
    assert s4 == IWDState.ESTIMATE_APPROVED

    s5 = get_next_state(IWDState.ESTIMATE_APPROVED, "issue_stock", "iwd_inventory_manager")
    assert s5 == IWDState.MATERIALS_ISSUED

    s6 = get_next_state(IWDState.MATERIALS_ISSUED, "start_execution", "iwd_engineer")
    assert s6 == IWDState.READY_FOR_EXECUTION

    s7 = get_next_state(IWDState.READY_FOR_EXECUTION, "work_complete", "iwd_engineer")
    assert s7 == IWDState.VERIFICATION_PENDING

    s8 = get_next_state(IWDState.VERIFICATION_PENDING, "verify_approved", "iwd_department_head")
    assert s8 == IWDState.RESOLVED

    s9 = get_next_state(IWDState.RESOLVED, "submit_bill", "iwd_engineer")
    assert s9 == IWDState.AUDIT_PENDING

    s10 = get_next_state(IWDState.AUDIT_PENDING, "audit_validate", "iwd_auditor")
    assert s10 == IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING

    s11 = get_next_state(
        IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING, "director_approve_payment", "iwd_director"
    )
    assert s11 == IWDState.ACCOUNTS_SETTLEMENT_PENDING

    s12 = get_next_state(IWDState.ACCOUNTS_SETTLEMENT_PENDING, "accounts_settle", "iwd_accounts")
    assert s12 == IWDState.SETTLED


def test_state_machine_invalid_transition_raises():
    """Verify invalid transition raises InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError):
        get_next_state(IWDState.SUBMITTED, "verify_approved", "iwd_department_head")


def test_state_machine_role_separation_dean_cannot_head_approve():
    """Verify Dean cannot approve or verify Department Head transitions (BR-IWD-018)."""
    with pytest.raises(RoleSeparationViolationError):
        get_next_state(IWDState.DEPARTMENT_HEAD_REVIEW_PENDING, "approve", "iwd_dean")

    with pytest.raises(RoleSeparationViolationError):
        get_next_state(IWDState.VERIFICATION_PENDING, "verify_approved", "iwd_dean")


def test_state_machine_rework_flow():
    """Verify single rework cycle allowed but second rework rejected (BW-IWD-10)."""
    # First rework allowed
    s1 = get_next_state(
        IWDState.VERIFICATION_PENDING,
        "verify_rework",
        "iwd_department_head",
        context={"rework_count": 0},
    )
    assert s1 == IWDState.REWORK_REQUIRED

    # Second rework must raise InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError, match="maximum attempts exceeded"):
        get_next_state(
            IWDState.VERIFICATION_PENDING,
            "verify_rework",
            "iwd_department_head",
            context={"rework_count": 1},
        )
