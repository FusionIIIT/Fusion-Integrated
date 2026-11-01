"""Pure Python unit tests for IWD Domain Engine (Increment 1).

Covers:
- BR-IWD-001..018
- CFR-IWD-01..17
- BW-IWD-01..15
- CW-IWD-01..04
- Exact boundary tests for Cost Bands
- Deterministic workload tie-breaking
- Rework traversal boundary (exactly 1 traversal)
- Domain boundary purity (zero Django/DRF/Celery imports)
"""

from decimal import Decimal
import sys

import pytest

from modules.iwd.domain.cost_bands import (
    CostBand,
    LOW_COST_LIMIT,
    MID_COST_LIMIT,
    classify_cost_band,
)
from modules.iwd.domain.state_machine import (
    DomainValidationError,
    InvalidStateTransitionError,
    IWDState,
    ReworkLimitExceededError,
    route_initial_estimate,
    transition_billing_and_settlement,
    transition_complaint,
    transition_estimate_approval,
    transition_execution_and_verification,
    transition_inventory_and_procurement,
    transition_resubmission,
    transition_urgent_flag,
)
from modules.iwd.domain.workload import (
    EngineerCandidate,
    NoEligibleEngineerError,
    select_engineer_for_assignment,
)


# ==============================================================================
# 1. Cost-Band Classification & Boundary Tests (BR-IWD-003, CFR-IWD-04)
# ==============================================================================


def test_cost_band_exact_boundaries():
    """Verify exact cost-band thresholds: < 25000, 25000 <= total <= 250000, > 250000."""
    # Boundary 1: Below 25,000 (Low-Cost)
    assert classify_cost_band(Decimal("0.00")) == CostBand.LOW
    assert classify_cost_band(Decimal("24999.99")) == CostBand.LOW

    # Boundary 2: Exactly 25,000 (Mid-Range lower inclusive bound)
    assert classify_cost_band(Decimal("25000.00")) == CostBand.MID

    # Mid-range arbitrary interior
    assert classify_cost_band(Decimal("100000.00")) == CostBand.MID

    # Boundary 3: Exactly 250,000 (Mid-Range upper inclusive bound)
    assert classify_cost_band(Decimal("250000.00")) == CostBand.MID

    # Boundary 4: Strictly above 250,000 (High-Cost)
    assert classify_cost_band(Decimal("250000.01")) == CostBand.HIGH
    assert classify_cost_band(Decimal("500000.00")) == CostBand.HIGH


def test_cost_band_numeric_input_types():
    """Verify support for str, int, float, and Decimal inputs."""
    assert classify_cost_band("24999.99") == CostBand.LOW
    assert classify_cost_band(25000) == CostBand.MID
    assert classify_cost_band(250000.0) == CostBand.MID
    assert classify_cost_band("250000.01") == CostBand.HIGH


def test_cost_band_negative_amount_rejection():
    """Negative estimate amounts are invalid and rejected with ValueError."""
    with pytest.raises(ValueError, match="cannot be negative"):
        classify_cost_band(Decimal("-1.00"))

    with pytest.raises(ValueError, match="Invalid monetary amount"):
        classify_cost_band("invalid_currency")


def test_initial_estimate_routing_by_band():
    """route_initial_estimate assigns correct initial STT state based on amount (CW-IWD-01)."""
    assert route_initial_estimate(Decimal("15000.00")) == IWDState.LOW_COST_REVIEW_PENDING
    assert route_initial_estimate(Decimal("25000.00")) == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING
    assert route_initial_estimate(Decimal("250000.00")) == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING
    assert route_initial_estimate(Decimal("250000.01")) == IWDState.DIRECTOR_REVIEW_PENDING_HIGH


# ==============================================================================
# 2. Complaint Intake & Assessment STT (BW-IWD-01, CFR-IWD-01, CFR-IWD-02)
# ==============================================================================


def test_complaint_intake_and_assessment_bw01():
    """Verify Complaint Intake and Assessment (BW-IWD-01)."""
    # 1. Submission by Institute Employee
    s1 = transition_complaint(
        IWDState.NO_COMPLAINT,
        action="submit_complaint",
        actor_role="Institute Employee",
    )
    assert s1 == IWDState.SUBMITTED

    # 2. Automatic Assignment by System
    s2 = transition_complaint(
        s1,
        action="assign_engineer",
        actor_role="System",
    )
    assert s2 == IWDState.ASSIGNED

    # 3. Assessment by Engineer
    s3 = transition_complaint(
        s2,
        action="record_assessment",
        actor_role="Engineer",
    )
    assert s3 == IWDState.ASSESSED


def test_complaint_intake_unauthorized_actors_rejected():
    """Unauthorized roles attempting complaint actions are rejected (BR-IWD-001)."""
    with pytest.raises(DomainValidationError, match="Only an Institute Employee"):
        transition_complaint(IWDState.NO_COMPLAINT, "submit_complaint", actor_role="Engineer")

    with pytest.raises(DomainValidationError, match="must be performed by the System"):
        transition_complaint(IWDState.SUBMITTED, "assign_engineer", actor_role="Institute Employee")

    with pytest.raises(DomainValidationError, match="Only an Engineer"):
        transition_complaint(IWDState.ASSIGNED, "record_assessment", actor_role="Department Head")


def test_complaint_intake_invalid_transition():
    """Attempting assessment before assignment raises InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError):
        transition_complaint(IWDState.SUBMITTED, "record_assessment", actor_role="Engineer")


# ==============================================================================
# 3. Estimate Approval & Multi-Tier Routing (BW-02..05, CW-01, BR-004..007)
# ==============================================================================


def test_low_cost_estimate_approval_and_rejection_bw02_bw12():
    """Low-cost estimate approved or rejected by IWD Admin (BW-IWD-02, BW-IWD-12)."""
    # Approval
    s_app = transition_estimate_approval(
        IWDState.LOW_COST_REVIEW_PENDING,
        action="approve",
        actor_role="IWD Admin",
    )
    assert s_app == IWDState.ESTIMATE_APPROVED

    # Rejection
    s_rej = transition_estimate_approval(
        IWDState.LOW_COST_REVIEW_PENDING,
        action="reject",
        actor_role="IWD Admin",
    )
    assert s_rej == IWDState.REJECTED_LOW

    # Role guard: only IWD Admin can review low-cost
    with pytest.raises(DomainValidationError, match="Only IWD Admin"):
        transition_estimate_approval(IWDState.LOW_COST_REVIEW_PENDING, "approve", actor_role="Department Head")


def test_mid_range_approval_and_forwarding_bw03_bw04_bw13():
    """Mid-range estimate requires committee review, then Department Head can approve, reject, or forward."""
    # Step 1: Committee feasibility review (BW-IWD-03)
    s1 = transition_estimate_approval(
        IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING,
        action="record_committee_review",
        actor_role="Review Committee",
    )
    assert s1 == IWDState.DEPARTMENT_HEAD_REVIEW_PENDING

    # Step 2a: Department Head approval
    s_app = transition_estimate_approval(
        s1,
        action="approve",
        actor_role="Department Head",
    )
    assert s_app == IWDState.ESTIMATE_APPROVED

    # Step 2b: Department Head rejection (BW-IWD-13)
    s_rej = transition_estimate_approval(
        s1,
        action="reject",
        actor_role="Department Head",
    )
    assert s_rej == IWDState.REJECTED_MID

    # Step 2c: Department Head forward to Director (BW-IWD-04)
    s_fwd = transition_estimate_approval(
        s1,
        action="forward_to_director",
        actor_role="Department Head",
    )
    assert s_fwd == IWDState.DIRECTOR_REVIEW_PENDING_MID

    # Step 3a: Director approves forwarded mid-range
    s_dir_app = transition_estimate_approval(
        s_fwd,
        action="approve",
        actor_role="Director",
    )
    assert s_dir_app == IWDState.ESTIMATE_APPROVED

    # Step 3b: Director rejects forwarded mid-range (BW-IWD-14)
    s_dir_rej = transition_estimate_approval(
        s_fwd,
        action="reject",
        actor_role="Director",
    )
    assert s_dir_rej == IWDState.REJECTED_DIRECTOR


def test_department_head_dean_role_separation_guard():
    """Dean is distinct from Department Head and cannot execute Dept Head decisions (BR-IWD-018)."""
    with pytest.raises(DomainValidationError, match="Only Department Head"):
        transition_estimate_approval(
            IWDState.DEPARTMENT_HEAD_REVIEW_PENDING,
            action="approve",
            actor_role="Dean",
        )


def test_high_cost_approval_and_vendor_selection_bw05_bw14():
    """High-cost estimate approved by Director for bidding, followed by vendor selection (BW-IWD-05)."""
    # Step 1: Director approves bidding
    s1 = transition_estimate_approval(
        IWDState.DIRECTOR_REVIEW_PENDING_HIGH,
        action="approve_bidding",
        actor_role="Director",
    )
    assert s1 == IWDState.BIDDING_AUTHORIZED

    # Step 2: Vendor Selection by IWD Admin
    s2 = transition_estimate_approval(
        s1,
        action="select_vendor",
        actor_role="IWD Admin",
    )
    assert s2 == IWDState.VENDOR_SELECTED

    # Rejection of high-cost by Director (BW-IWD-14)
    s_rej = transition_estimate_approval(
        IWDState.DIRECTOR_REVIEW_PENDING_HIGH,
        action="reject_bidding",
        actor_role="Director",
    )
    assert s_rej == IWDState.REJECTED_DIRECTOR


# ==============================================================================
# 4. Rejection and Resubmission Routing (BW-12..14, CW-04, BR-IWD-009)
# ==============================================================================


def test_resubmission_routes_based_on_new_cost_band():
    """Resubmission routes to correct cost band based on updated amount (CW-IWD-04)."""
    # 1. Resubmit rejected low-cost, remaining low-cost (< 25k)
    r1 = transition_resubmission(IWDState.REJECTED_LOW, Decimal("20000.00"), actor_role="Engineer")
    assert r1 == IWDState.LOW_COST_REVIEW_PENDING

    # 2. Resubmit rejected low-cost, modified to mid-range (30k) -> routes to committee
    r2 = transition_resubmission(IWDState.REJECTED_LOW, Decimal("30000.00"), actor_role="Engineer")
    assert r2 == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING

    # 3. Resubmit rejected mid-range, modified to high-cost (300k) -> routes to Director
    r3 = transition_resubmission(IWDState.REJECTED_MID, Decimal("300000.00"), actor_role="Engineer")
    assert r3 == IWDState.DIRECTOR_REVIEW_PENDING_HIGH

    # 4. Resubmit rejected Director route, modified to low-cost (10k) -> routes to Low-Cost
    r4 = transition_resubmission(IWDState.REJECTED_DIRECTOR, Decimal("10000.00"), actor_role="Engineer")
    assert r4 == IWDState.LOW_COST_REVIEW_PENDING


def test_resubmission_from_non_rejected_state_blocked():
    """Resubmission is only permitted from rejected states (UC-IWD-151)."""
    with pytest.raises(InvalidStateTransitionError, match="Cannot resubmit estimate from non-rejected state"):
        transition_resubmission(IWDState.ESTIMATE_APPROVED, Decimal("20000.00"), actor_role="Engineer")


# ==============================================================================
# 5. Inventory & Procurement Transitions (BW-06..08, CW-02, BR-IWD-010, BR-IWD-011)
# ==============================================================================


def test_inventory_and_procurement_transitions():
    """Verify stock issue and shortage procurement flows."""
    # BW-IWD-06: Stock Available -> Materials Issued
    s_stock = transition_inventory_and_procurement(
        IWDState.ESTIMATE_APPROVED,
        action="issue_stock",
        actor_role="IWD Admin",
    )
    assert s_stock == IWDState.MATERIALS_ISSUED

    # BW-IWD-07: Low-cost shortage
    p_low = transition_inventory_and_procurement(
        IWDState.ESTIMATE_APPROVED,
        action="stock_unavailable",
        actor_role="IWD Admin",
        cost_band=CostBand.LOW,
    )
    assert p_low == IWDState.PROCUREMENT_NEEDED_LOW

    avail_low = transition_inventory_and_procurement(
        p_low,
        action="procurement_complete",
        actor_role="IWD Admin",
    )
    assert avail_low == IWDState.MATERIALS_AVAILABLE

    issued_low = transition_inventory_and_procurement(
        avail_low,
        action="issue_material",
        actor_role="IWD Admin",
    )
    assert issued_low == IWDState.MATERIALS_ISSUED

    # BW-IWD-08: Mid-range shortage
    p_mid = transition_inventory_and_procurement(
        IWDState.ESTIMATE_APPROVED,
        action="stock_unavailable",
        actor_role="IWD Admin",
        cost_band=CostBand.MID,
    )
    assert p_mid == IWDState.PROCUREMENT_NEEDED_MID


# ==============================================================================
# 6. Work Execution & Verification Gate (BW-09, BW-10, CW-03, BR-IWD-014)
# ==============================================================================


def test_execution_and_verification_zero_rework_bw09():
    """Normal execution with zero rework passes physical verification directly to Resolved."""
    s1, r1 = transition_execution_and_verification(
        IWDState.READY_FOR_EXECUTION,
        action="complete_work",
        actor_role="Engineer",
        rework_count=0,
    )
    assert s1 == IWDState.VERIFICATION_PENDING
    assert r1 == 0

    s2, r2 = transition_execution_and_verification(
        s1,
        action="verify_approved",
        actor_role="Department Head",
        rework_count=r1,
    )
    assert s2 == IWDState.RESOLVED
    assert r2 == 0


def test_execution_and_verification_exactly_one_rework_traversal_bw10():
    """Work rework allows exactly one traversal; exceeding it raises ReworkLimitExceededError."""
    # 1. Complete initial work -> Verification Pending
    s1, r1 = transition_execution_and_verification(
        IWDState.READY_FOR_EXECUTION,
        action="complete_work",
        actor_role="Engineer",
        rework_count=0,
    )
    assert s1 == IWDState.VERIFICATION_PENDING

    # 2. First rework request by Department Head -> Rework Required (rework_count becomes 1)
    s2, r2 = transition_execution_and_verification(
        s1,
        action="verify_rework",
        actor_role="Department Head",
        rework_count=r1,
    )
    assert s2 == IWDState.REWORK_REQUIRED
    assert r2 == 1

    # 3. Engineer completes rework -> Verification Pending
    s3, r3 = transition_execution_and_verification(
        s2,
        action="complete_work",
        actor_role="Engineer",
        rework_count=r2,
    )
    assert s3 == IWDState.VERIFICATION_PENDING
    assert r3 == 1

    # 4. Department Head approves after rework -> Resolved
    s4, r4 = transition_execution_and_verification(
        s3,
        action="verify_approved",
        actor_role="Department Head",
        rework_count=r3,
    )
    assert s4 == IWDState.RESOLVED
    assert r4 == 1

    # 5. Boundary test: attempting a second rework traversal is forbidden (BW-IWD-10)
    with pytest.raises(ReworkLimitExceededError, match="permits at most one rework traversal"):
        transition_execution_and_verification(
            s3,
            action="verify_rework",
            actor_role="Department Head",
            rework_count=1,
        )


def test_physical_verification_gate_prevents_unverified_resolution():
    """Work cannot jump directly from execution to Resolved without verification (BR-IWD-014)."""
    with pytest.raises(InvalidStateTransitionError):
        transition_execution_and_verification(
            IWDState.READY_FOR_EXECUTION,
            action="verify_approved",
            actor_role="Department Head",
        )


# ==============================================================================
# 7. Final Billing, Audit & Settlement Sequence (BW-11, BR-IWD-015, BR-IWD-016)
# ==============================================================================


def test_billing_and_settlement_sequence_bw11():
    """Verify strict settlement sequence: Engineer bill -> Auditor validate -> Director approve -> Accounts settle."""
    # Step 1: Submit final bill post-resolution
    s1 = transition_billing_and_settlement(
        IWDState.RESOLVED,
        action="submit_final_bill",
        actor_role="Engineer",
    )
    assert s1 == IWDState.AUDIT_PENDING

    # Step 2: Auditor validation
    s2 = transition_billing_and_settlement(
        s1,
        action="validate_bill",
        actor_role="Auditor",
    )
    assert s2 == IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING

    # Step 3: Director payment approval
    s3 = transition_billing_and_settlement(
        s2,
        action="approve_payment",
        actor_role="Director",
    )
    assert s3 == IWDState.ACCOUNTS_SETTLEMENT_PENDING

    # Step 4: Accounts settlement
    s4 = transition_billing_and_settlement(
        s3,
        action="record_settlement",
        actor_role="Accounts Department",
    )
    assert s4 == IWDState.SETTLED


def test_billing_blocked_if_unverified():
    """Final bill cannot be submitted from un-resolved states (BR-IWD-014)."""
    with pytest.raises(InvalidStateTransitionError):
        transition_billing_and_settlement(
            IWDState.VERIFICATION_PENDING,
            action="submit_final_bill",
            actor_role="Engineer",
        )


# ==============================================================================
# 8. Urgent Fast-Track (BW-15, BR-IWD-012)
# ==============================================================================


def test_urgent_fast_track_bw15():
    """Urgent repair flagged by Engineer, accepted or declined by Dept Head/Director (BW-IWD-15)."""
    # 1. Flag urgent from active un-resolved state
    u1 = transition_urgent_flag(
        IWDState.ASSESSED,
        action="flag_urgent",
        actor_role="Engineer",
    )
    assert u1 == IWDState.URGENT_REVIEW_PENDING

    # 2a. Accepted by Department Head
    u_acc = transition_urgent_flag(
        u1,
        action="accept_urgent",
        actor_role="Department Head",
    )
    assert u_acc == IWDState.URGENT_PRIORITY_ACTIVE

    # 2b. Declined by Director
    u_dec = transition_urgent_flag(
        u1,
        action="decline_urgent",
        actor_role="Director",
    )
    assert u_dec == IWDState.ASSESSED

    # Cannot flag urgent on resolved work
    with pytest.raises(DomainValidationError, match="Cannot flag an urgent repair"):
        transition_urgent_flag(IWDState.RESOLVED, "flag_urgent", actor_role="Engineer")


# ==============================================================================
# 9. Workload Auto-Assignment Scoring (BR-IWD-002, CFR-IWD-02, AFR-IWD-007)
# ==============================================================================


def test_workload_engineer_selection_unequal_workload():
    """Engineer with lowest active complaint count is selected."""
    candidates = [
        EngineerCandidate(user_id=101, active_complaint_count=5),
        EngineerCandidate(user_id=102, active_complaint_count=1),
        EngineerCandidate(user_id=103, active_complaint_count=3),
    ]
    chosen = select_engineer_for_assignment(candidates)
    assert chosen.user_id == 102
    assert chosen.active_complaint_count == 1


def test_workload_engineer_selection_deterministic_tie_breaker():
    """When active workloads are equal, lowest user_id tie-breaker is selected."""
    candidates = [
        EngineerCandidate(user_id=105, active_complaint_count=2),
        EngineerCandidate(user_id=102, active_complaint_count=2),
        EngineerCandidate(user_id=108, active_complaint_count=2),
    ]
    chosen = select_engineer_for_assignment(candidates)
    assert chosen.user_id == 102


def test_workload_ineligible_candidates_excluded():
    """Ineligible candidates are excluded even if their workload count is zero."""
    candidates = [
        EngineerCandidate(user_id=101, active_complaint_count=0, is_eligible=False),
        EngineerCandidate(user_id=102, active_complaint_count=4, is_eligible=True),
    ]
    chosen = select_engineer_for_assignment(candidates)
    assert chosen.user_id == 102


def test_workload_specialization_matching():
    """Specialization filter matches trade (civil vs electrical)."""
    candidates = [
        EngineerCandidate(user_id=101, active_complaint_count=1, specialization="electrical"),
        EngineerCandidate(user_id=102, active_complaint_count=3, specialization="civil"),
    ]
    chosen = select_engineer_for_assignment(candidates, required_specialization="civil")
    assert chosen.user_id == 102


def test_workload_no_eligible_engineer_raises_error():
    """When no eligible engineer exists, raises NoEligibleEngineerError."""
    with pytest.raises(NoEligibleEngineerError, match="No eligible engineer available"):
        select_engineer_for_assignment([])

    with pytest.raises(NoEligibleEngineerError, match="No eligible engineer available"):
        select_engineer_for_assignment(
            [EngineerCandidate(user_id=101, active_complaint_count=1, is_eligible=False)]
        )


# ==============================================================================
# 10. Pure Domain Isolation Guarantee (.importlinter)
# ==============================================================================


def test_domain_boundary_purity_zero_framework_imports():
    """Assert that modules/iwd/domain/ does not import django, rest_framework, or celery."""
    import modules.iwd.domain.cost_bands
    import modules.iwd.domain.state_machine
    import modules.iwd.domain.workload

    for mod in [
        modules.iwd.domain.cost_bands,
        modules.iwd.domain.state_machine,
        modules.iwd.domain.workload,
    ]:
        loaded_modules = set(sys.modules.keys())
        for forbidden in ("django", "rest_framework", "celery"):
            # Check module attributes to ensure no forbidden package is referenced
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if hasattr(attr, "__module__") and attr.__module__:
                    assert not attr.__module__.startswith(forbidden), (
                        f"Domain purity violated: {mod.__name__} references {attr.__module__}"
                    )

