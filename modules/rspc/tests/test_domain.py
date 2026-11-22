"""RSPC Domain tests: pure Python, no database, executed in milliseconds."""

from decimal import Decimal

import pytest

from modules.rspc.domain.entities import (
    BudgetHeadEntity,
    ProjectStatus,
    ProposalStatus,
)
from modules.rspc.domain.invariants import (
    InvariantViolationError,
    calculate_institutional_overheads,
    validate_budget_head_positive,
    validate_disbursement,
    validate_extension_request,
)
from modules.rspc.domain.state_machine import (
    DomainTransitionError,
    ProjectLifecycleStateMachine,
    ProposalStateMachine,
)

# -- State Machine Tests -------------------------------------------------------


def test_proposal_happy_path_transitions():
    """Test standard progression: DRAFT -> SUBMITTED_HOD -> ENDORSED_HOD -> APPROVED_DEAN."""
    pi_id = 101
    hod_id = 202
    dean_id = 303

    s1 = ProposalStateMachine.transition(ProposalStatus.DRAFT, "submit", "faculty", pi_id, pi_id)
    assert s1 == ProposalStatus.SUBMITTED_HOD

    s2 = ProposalStateMachine.transition(s1, "endorse", "hod", pi_id, hod_id)
    assert s2 == ProposalStatus.ENDORSED_HOD

    s3 = ProposalStateMachine.transition(s2, "approve", "dean", pi_id, dean_id)
    assert s3 == ProposalStatus.APPROVED_DEAN


def test_proposal_conflict_of_interest_guard():
    """BR-RSPC-004: PI cannot endorse or approve their own proposal."""
    pi_id = 101
    with pytest.raises(DomainTransitionError, match="Conflict of interest"):
        ProposalStateMachine.transition(
            ProposalStatus.SUBMITTED_HOD, "endorse", "hod", pi_id, pi_id
        )

    with pytest.raises(DomainTransitionError, match="Conflict of interest"):
        ProposalStateMachine.transition(
            ProposalStatus.ENDORSED_HOD, "approve", "dean", pi_id, pi_id
        )


def test_proposal_illegal_transition_raises():
    """Cannot jump directly from DRAFT to APPROVED_DEAN."""
    with pytest.raises(DomainTransitionError, match="Illegal transition"):
        ProposalStateMachine.transition(ProposalStatus.DRAFT, "approve", "dean", 101, 303)


def test_project_lifecycle_state_machine():
    """Test project lifecycle states: SANCTIONED -> ACTIVE -> EXTENSION_REQUESTED -> ACTIVE."""
    s1 = ProjectLifecycleStateMachine.transition(ProjectStatus.SANCTIONED, "activate", "admin")
    assert s1 == ProjectStatus.ACTIVE

    s2 = ProjectLifecycleStateMachine.transition(s1, "request_extension", "faculty")
    assert s2 == ProjectStatus.EXTENSION_REQUESTED

    s3 = ProjectLifecycleStateMachine.transition(s2, "approve_extension", "dean")
    assert s3 == ProjectStatus.ACTIVE


def test_project_illegal_closure_without_pending():
    with pytest.raises(DomainTransitionError, match="Illegal transition"):
        ProjectLifecycleStateMachine.transition(ProjectStatus.ACTIVE, "approve_closure", "dean")


# -- Invariants & Business Rule Tests ------------------------------------------


def test_budget_head_available_balance():
    head = BudgetHeadEntity(
        head_type="equipment",
        allocated_amount=Decimal("100000.00"),
        spent_amount=Decimal("40000.00"),
        committed_amount=Decimal("10000.00"),
    )
    assert head.available_balance == Decimal("50000.00")


def test_disbursement_within_balance_passes():
    validate_disbursement(
        head_name="equipment",
        available_balance=Decimal("50000.00"),
        requested_amount=Decimal("30000.00"),
    )


def test_disbursement_exceeding_balance_raises():
    """BR-RSPC-003: Deficit prohibition."""
    with pytest.raises(InvariantViolationError, match="Insufficient balance"):
        validate_disbursement(
            head_name="consumables",
            available_balance=Decimal("10000.00"),
            requested_amount=Decimal("15000.00"),
        )


def test_overhead_calculation():
    """BR-RSPC-002: Institutional overhead computation."""
    direct = Decimal("1000000.00")
    rate = Decimal("20.00")  # 20%
    overhead = calculate_institutional_overheads(direct, rate)
    assert overhead == Decimal("200000.00")


def test_extension_limit_guard():
    """BR-RSPC-005: Extensions > 12 cumulative months require Director approval."""
    # Under 12 months with Dean passes
    validate_extension_request(requested_months=6, cumulative_months=4, approver_role="dean")

    # Over 12 months with Dean fails
    with pytest.raises(InvariantViolationError, match="require Director approval"):
        validate_extension_request(requested_months=6, cumulative_months=8, approver_role="dean")

    # Over 12 months with Director passes
    validate_extension_request(requested_months=6, cumulative_months=8, approver_role="director")


def test_budget_head_positive_guard():
    with pytest.raises(InvariantViolationError, match="cannot be negative"):
        validate_budget_head_positive(Decimal("-10.00"), "travel")
    validate_budget_head_positive(Decimal("0.00"), "travel")
    validate_budget_head_positive(Decimal("500.00"), "travel")


def test_disbursement_non_positive_guard():
    with pytest.raises(InvariantViolationError, match="must be strictly positive"):
        validate_disbursement("consumables", Decimal("100.00"), Decimal("0.00"))
    with pytest.raises(InvariantViolationError, match="must be strictly positive"):
        validate_disbursement("consumables", Decimal("100.00"), Decimal("-50.00"))


def test_overhead_negative_guard():
    with pytest.raises(InvariantViolationError, match="must be non-negative"):
        calculate_institutional_overheads(Decimal("-100.00"), Decimal("10.00"))
    with pytest.raises(InvariantViolationError, match="must be non-negative"):
        calculate_institutional_overheads(Decimal("100.00"), Decimal("-5.00"))


def test_extension_zero_months_guard():
    with pytest.raises(InvariantViolationError, match="at least 1 month"):
        validate_extension_request(requested_months=0, cumulative_months=0, approver_role="dean")
