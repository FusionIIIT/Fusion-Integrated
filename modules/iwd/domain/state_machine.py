"""Pure Python state machine and transition engine for IWD.

Implements authoritative State-Transition Tables (STTs) from:
- 05_IWD_Workflow_Specifications_v1.4_FINAL (BW-IWD-01..15, CW-IWD-01..04)
- 04_IWD_Business_Rule_Specifications_v1.4_FINAL (BR-IWD-001..018)
- 02_IWD_Requirement_Registry_CFR_AFR_v1.2_FINAL

Explicitly retired workflows (excluded):
- BW-IWD-16, BW-IWD-17 (Unsupported inferred Dean mid-range route)
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from modules.iwd.domain.cost_bands import CostBand, classify_cost_band


class IWDDomainError(Exception):
    """Base domain exception for IWD module."""


class InvalidStateTransitionError(IWDDomainError):
    """Raised when an illegal or unsupported state transition is attempted."""


class DomainValidationError(IWDDomainError):
    """Raised when domain constraints or guards are violated."""


class ReworkLimitExceededError(IWDDomainError):
    """Raised when physical verification rework exceeds the single permitted traversal (BW-IWD-10)."""


class IWDState(str, Enum):
    """Canonical lifecycle states matching the authoritative STTs in Workflow Specifications v1.4."""

    # 1. Complaint Intake & Assessment (BW-IWD-01)
    NO_COMPLAINT = "No Complaint"
    SUBMITTED = "Submitted"
    ASSIGNED = "Assigned"
    ASSESSED = "Assessed"

    # 2. Estimate Approval States (BW-IWD-02..05, CW-IWD-01)
    LOW_COST_REVIEW_PENDING = "Low-Cost Review Pending"
    MID_RANGE_COMMITTEE_REVIEW_PENDING = "Mid-Range Committee Review Pending"
    DEPARTMENT_HEAD_REVIEW_PENDING = "Department Head Review Pending"
    DIRECTOR_REVIEW_PENDING_MID = "Director Review Pending (Mid-Range)"
    DIRECTOR_REVIEW_PENDING_HIGH = "Director Review Pending (High-Cost)"
    ESTIMATE_APPROVED = "Estimate Approved"

    # 3. High-Cost Bidding & Vendor Selection (BW-IWD-05)
    BIDDING_AUTHORIZED = "Bidding Authorized"
    VENDOR_SELECTED = "Vendor/Contractor Selected"

    # 4. Inventory & Procurement (BW-IWD-06..08, CW-IWD-02)
    PROCUREMENT_NEEDED_LOW = "Procurement Needed (Low)"
    PROCUREMENT_NEEDED_MID = "Procurement Needed (Mid)"
    MATERIALS_AVAILABLE = "Materials Available"
    MATERIALS_ISSUED = "Materials Issued"

    # 5. Execution, Rework & Physical Verification (BW-IWD-09, BW-IWD-10, CW-IWD-03)
    READY_FOR_EXECUTION = "Ready for Execution"
    VERIFICATION_PENDING = "Verification Pending"
    REWORK_REQUIRED = "Rework Required"
    RESOLVED = "Resolved"

    # 6. Final Billing, Audit & Settlement (BW-IWD-11)
    AUDIT_PENDING = "Audit Pending"
    DIRECTOR_PAYMENT_APPROVAL_PENDING = "Director Payment Approval Pending"
    ACCOUNTS_SETTLEMENT_PENDING = "Accounts Settlement Pending"
    SETTLED = "Settled"

    # 7. Rejection States (BW-IWD-12..14, CW-IWD-04)
    REJECTED_LOW = "Rejected - Low-Cost"
    REJECTED_MID = "Rejected - Mid-Range"
    REJECTED_DIRECTOR = "Rejected - Director Route"

    # 8. Urgent Fast-Track (BW-IWD-15)
    URGENT_REVIEW_PENDING = "Urgent Review Pending"
    URGENT_PRIORITY_ACTIVE = "Urgent Priority Active"


# Set of terminal / post-resolution states where active work is completed
TERMINAL_STATES = frozenset({IWDState.SETTLED})


def transition_complaint(
    current_state: IWDState,
    action: str,
    actor_role: str,
) -> IWDState:
    """Execute state transition for Complaint Intake and Assessment (BW-IWD-01).

    STT:
    - No Complaint + submit_complaint (Institute Employee) -> Submitted
    - Submitted + assign_engineer (System) -> Assigned
    - Assigned + record_assessment (Engineer) -> Assessed
    """
    if current_state == IWDState.NO_COMPLAINT and action == "submit_complaint":
        if actor_role != "Institute Employee":
            raise DomainValidationError("Only an Institute Employee may submit a complaint (BR-IWD-001).")
        return IWDState.SUBMITTED

    if current_state == IWDState.SUBMITTED and action == "assign_engineer":
        if actor_role != "System":
            raise DomainValidationError("Assignment must be performed by the System (BR-IWD-002).")
        return IWDState.ASSIGNED

    if current_state == IWDState.ASSIGNED and action == "record_assessment":
        if actor_role != "Engineer":
            raise DomainValidationError("Only an Engineer may record repair assessments (BR-IWD-001).")
        return IWDState.ASSESSED

    raise InvalidStateTransitionError(
        f"Invalid complaint transition from '{current_state.value}' with action '{action}' by '{actor_role}'."
    )


def route_initial_estimate(amount: Decimal | str | int | float) -> IWDState:
    """Determine initial approval state for a submitted estimate based on cost band (CW-IWD-01).

    - total < Rs. 25,000 -> Low-Cost Review Pending (BW-IWD-02)
    - Rs. 25,000 <= total <= Rs. 2.5 lakh -> Mid-Range Committee Review Pending (BW-IWD-03)
    - total > Rs. 2.5 lakh -> Director Review Pending (High-Cost) (BW-IWD-05)
    """
    band = classify_cost_band(amount)
    if band == CostBand.LOW:
        return IWDState.LOW_COST_REVIEW_PENDING
    elif band == CostBand.MID:
        return IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING
    else:
        return IWDState.DIRECTOR_REVIEW_PENDING_HIGH


def transition_estimate_approval(
    current_state: IWDState,
    action: str,
    actor_role: str,
) -> IWDState:
    """Execute approval transitions across all cost bands (BW-IWD-02..05, CW-IWD-01).

    STTs:
    - BW-IWD-02:
        Low-Cost Review Pending + approve (IWD Admin) -> Estimate Approved
        Low-Cost Review Pending + reject (IWD Admin) -> Rejected - Low-Cost (BW-IWD-12)
    - BW-IWD-03:
        Mid-Range Committee Review Pending + record_committee_review (Review Committee) -> Department Head Review Pending
        Department Head Review Pending + approve (Department Head) -> Estimate Approved
        Department Head Review Pending + reject (Department Head) -> Rejected - Mid-Range (BW-IWD-13)
    - BW-IWD-04:
        Department Head Review Pending + forward_to_director (Department Head) -> Director Review Pending (Mid-Range)
        Director Review Pending (Mid-Range) + approve (Director) -> Estimate Approved
        Director Review Pending (Mid-Range) + reject (Director) -> Rejected - Director Route (BW-IWD-14)
    - BW-IWD-05:
        Director Review Pending (High-Cost) + approve_bidding (Director) -> Bidding Authorized
        Director Review Pending (High-Cost) + reject_bidding (Director) -> Rejected - Director Route (BW-IWD-14)
        Bidding Authorized + select_vendor (IWD Admin) -> Vendor/Contractor Selected
    """
    # Low-Cost Path (BW-IWD-02, BW-IWD-12)
    if current_state == IWDState.LOW_COST_REVIEW_PENDING:
        if actor_role != "IWD Admin":
            raise DomainValidationError("Only IWD Admin may review low-cost estimates (BR-IWD-004).")
        if action == "approve":
            return IWDState.ESTIMATE_APPROVED
        if action == "reject":
            return IWDState.REJECTED_LOW

    # Mid-Range Committee Path (BW-IWD-03)
    if current_state == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING:
        if actor_role not in ("Review Committee", "Department Head"):
            raise DomainValidationError("Only Review Committee may record committee feasibility review (BR-IWD-005).")
        if action == "record_committee_review":
            return IWDState.DEPARTMENT_HEAD_REVIEW_PENDING

    # Department Head Mid-Range Decision (BW-IWD-03, BW-IWD-04, BW-IWD-13)
    if current_state == IWDState.DEPARTMENT_HEAD_REVIEW_PENDING:
        if actor_role != "Department Head":
            raise DomainValidationError("Only Department Head may make this supervisory decision (BR-IWD-006, BR-IWD-018).")
        if action == "approve":
            return IWDState.ESTIMATE_APPROVED
        if action == "reject":
            return IWDState.REJECTED_MID
        if action == "forward_to_director":
            return IWDState.DIRECTOR_REVIEW_PENDING_MID

    # Director Review for Forwarded Mid-Range (BW-IWD-04, BW-IWD-14)
    if current_state == IWDState.DIRECTOR_REVIEW_PENDING_MID:
        if actor_role != "Director":
            raise DomainValidationError("Only Director may approve forwarded mid-range requests (BR-IWD-006).")
        if action == "approve":
            return IWDState.ESTIMATE_APPROVED
        if action == "reject":
            return IWDState.REJECTED_DIRECTOR

    # Director Review for High-Cost (BW-IWD-05, BW-IWD-14)
    if current_state == IWDState.DIRECTOR_REVIEW_PENDING_HIGH:
        if actor_role != "Director":
            raise DomainValidationError("Only Director may approve high-cost bidding authorization (BR-IWD-007).")
        if action in ("approve", "approve_bidding"):
            return IWDState.BIDDING_AUTHORIZED
        if action in ("reject", "reject_bidding"):
            return IWDState.REJECTED_DIRECTOR

    # Vendor Selection (BW-IWD-05)
    if current_state == IWDState.BIDDING_AUTHORIZED:
        if actor_role != "IWD Admin":
            raise DomainValidationError("Only IWD Admin may record vendor selection (BR-IWD-007, BR-IWD-008).")
        if action == "select_vendor":
            return IWDState.VENDOR_SELECTED

    raise InvalidStateTransitionError(
        f"Invalid estimate approval transition from '{current_state.value}' with action '{action}' by '{actor_role}'."
    )


def transition_resubmission(
    current_state: IWDState,
    new_amount: Decimal | str | int | float,
    actor_role: str,
) -> IWDState:
    """Resubmit a rejected estimate, routing to the appropriate cost band (BW-IWD-12..14, CW-IWD-04).

    STT:
    - Rejected - Low-Cost / Rejected - Mid-Range / Rejected - Director Route + resubmit_estimate
      -> routes to corresponding review stage based on current new_amount (BR-IWD-009, CW-IWD-04).
    """
    valid_rejected_states = {
        IWDState.REJECTED_LOW,
        IWDState.REJECTED_MID,
        IWDState.REJECTED_DIRECTOR,
    }
    if current_state not in valid_rejected_states:
        raise InvalidStateTransitionError(
            f"Cannot resubmit estimate from non-rejected state '{current_state.value}' (BR-IWD-009, UC-IWD-151)."
        )

    if actor_role != "Engineer":
        raise DomainValidationError("Only the responsible Engineer may modify and resubmit an estimate.")

    band = classify_cost_band(new_amount)
    if band == CostBand.LOW:
        return IWDState.LOW_COST_REVIEW_PENDING
    elif band == CostBand.MID:
        return IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING
    else:
        return IWDState.DIRECTOR_REVIEW_PENDING_HIGH


def transition_inventory_and_procurement(
    current_state: IWDState,
    action: str,
    actor_role: str,
    cost_band: CostBand | None = None,
) -> IWDState:
    """Execute inventory check, material issuance, or stock shortage procurement (BW-IWD-06..08, CW-IWD-02).

    STTs:
    - BW-IWD-06: Estimate Approved + check_and_issue_stock (stock available) -> Materials Issued
    - BW-IWD-07: Estimate Approved + stock_unavailable (low-cost) -> Procurement Needed (Low)
                 Procurement Needed (Low) + procurement_complete -> Materials Available
                 Materials Available + issue_material -> Materials Issued
    - BW-IWD-08: Estimate Approved + stock_unavailable (mid-range) -> Procurement Needed (Mid)
                 Procurement Needed (Mid) + procurement_complete -> Materials Available
                 Materials Available + issue_material -> Materials Issued
    """
    if actor_role != "IWD Admin":
        raise DomainValidationError("Only IWD Admin may perform inventory/procurement actions (BR-IWD-010).")

    if current_state == IWDState.ESTIMATE_APPROVED:
        if action == "issue_stock":
            return IWDState.MATERIALS_ISSUED
        if action == "stock_unavailable":
            if cost_band == CostBand.LOW:
                return IWDState.PROCUREMENT_NEEDED_LOW
            elif cost_band == CostBand.MID:
                return IWDState.PROCUREMENT_NEEDED_MID
            elif cost_band == CostBand.HIGH:
                raise DomainValidationError(
                    "High-cost works (> ₹2.5L) use external bidding (BR-IWD-007) and cannot use inventory stock shortage procurement."
                )
            else:
                raise DomainValidationError("Cost band must be provided when stock is unavailable.")

    if current_state in (IWDState.PROCUREMENT_NEEDED_LOW, IWDState.PROCUREMENT_NEEDED_MID):
        if action == "procurement_complete":
            return IWDState.MATERIALS_AVAILABLE

    if current_state == IWDState.MATERIALS_AVAILABLE:
        if action == "issue_material":
            return IWDState.MATERIALS_ISSUED

    raise InvalidStateTransitionError(
        f"Invalid inventory/procurement transition from '{current_state.value}' with action '{action}' by '{actor_role}'."
    )


def transition_execution_and_verification(
    current_state: IWDState,
    action: str,
    actor_role: str,
    rework_count: int = 0,
) -> tuple[IWDState, int]:
    """Execute work completion, rework traversal, and physical verification (BW-IWD-09, BW-IWD-10, CW-IWD-03).

    Constraint: Exactly one rework traversal permitted (BW-IWD-10). Zero rework in BW-IWD-09.

    STT:
    - Ready for Execution + complete_work (Engineer) -> Verification Pending
    - Verification Pending + verify_approved (Department Head) -> Resolved (BR-IWD-014)
    - Verification Pending + verify_rework (Department Head) -> Rework Required (BR-IWD-014)
    - Rework Required + complete_work (Engineer) -> Verification Pending

    Returns:
        tuple[IWDState, int]: (resulting_state, updated_rework_count)
    """
    # 1. Engineer completion
    if current_state in (IWDState.READY_FOR_EXECUTION, IWDState.MATERIALS_ISSUED, IWDState.VENDOR_SELECTED):
        if action == "complete_work":
            if actor_role != "Engineer":
                raise DomainValidationError("Only Engineer may mark repair work complete (BR-IWD-001).")
            return IWDState.VERIFICATION_PENDING, rework_count

    if current_state == IWDState.REWORK_REQUIRED and action == "complete_work":
        if actor_role != "Engineer":
            raise DomainValidationError("Only Engineer may mark rework complete (BR-IWD-001).")
        return IWDState.VERIFICATION_PENDING, rework_count

    # 2. Department Head Physical Verification (BR-IWD-014, BR-IWD-018)
    if current_state == IWDState.VERIFICATION_PENDING:
        if actor_role != "Department Head":
            raise DomainValidationError("Only Department Head may conduct physical quality verification (BR-IWD-014, BR-IWD-018).")
        if action == "verify_approved":
            return IWDState.RESOLVED, rework_count
        if action == "verify_rework":
            if rework_count >= 1:
                raise ReworkLimitExceededError(
                    "Physical verification permits at most one rework traversal (BW-IWD-10)."
                )
            return IWDState.REWORK_REQUIRED, rework_count + 1

    raise InvalidStateTransitionError(
        f"Invalid execution/verification transition from '{current_state.value}' with action '{action}' by '{actor_role}'."
    )


def transition_billing_and_settlement(
    current_state: IWDState,
    action: str,
    actor_role: str,
) -> IWDState:
    """Execute billing, financial audit, Director payment approval, and Accounts settlement (BW-IWD-11).

    STT:
    - Resolved + submit_final_bill (Engineer) -> Audit Pending (BR-IWD-014)
    - Audit Pending + validate_bill (Auditor) -> Director Payment Approval Pending (BR-IWD-015)
    - Director Payment Approval Pending + approve_payment (Director) -> Accounts Settlement Pending (BR-IWD-016)
    - Accounts Settlement Pending + record_settlement (Accounts Department) -> Settled (BR-IWD-016)
    """
    if current_state == IWDState.RESOLVED and action == "submit_final_bill":
        if actor_role != "Engineer":
            raise DomainValidationError("Only Engineer may submit the final bill (BR-IWD-001).")
        return IWDState.AUDIT_PENDING

    if current_state == IWDState.AUDIT_PENDING and action == "validate_bill":
        if actor_role != "Auditor":
            raise DomainValidationError("Only Auditor may validate the final bill (BR-IWD-015).")
        return IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING

    if current_state == IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING and action == "approve_payment":
        if actor_role != "Director":
            raise DomainValidationError("Only Director may grant final payment approval (BR-IWD-016).")
        return IWDState.ACCOUNTS_SETTLEMENT_PENDING

    if current_state == IWDState.ACCOUNTS_SETTLEMENT_PENDING and action == "record_settlement":
        if actor_role != "Accounts Department":
            raise DomainValidationError("Only Accounts Department may record settlement (BR-IWD-016).")
        return IWDState.SETTLED

    raise InvalidStateTransitionError(
        f"Invalid billing/settlement transition from '{current_state.value}' with action '{action}' by '{actor_role}'."
    )


def transition_urgent_flag(
    current_state: IWDState,
    action: str,
    actor_role: str,
) -> IWDState:
    """Execute urgent fast-track review transitions (BW-IWD-15).

    STT:
    - Active un-resolved state + flag_urgent (Engineer) -> Urgent Review Pending (BR-IWD-012)
    - Urgent Review Pending + accept_urgent (Department Head or Director) -> Urgent Priority Active
    - Urgent Review Pending + decline_urgent (Department Head or Director) -> Returns to prior normal state
    """
    if action == "flag_urgent":
        if actor_role != "Engineer":
            raise DomainValidationError("Only Engineer may flag an urgent repair (BR-IWD-012).")
        if current_state in (IWDState.RESOLVED, IWDState.SETTLED):
            raise DomainValidationError("Cannot flag an urgent repair on resolved or settled work.")
        return IWDState.URGENT_REVIEW_PENDING

    if current_state == IWDState.URGENT_REVIEW_PENDING:
        if actor_role not in ("Department Head", "Director"):
            raise DomainValidationError(
                "Only Department Head or Director may review urgent escalation (BR-IWD-012, BR-IWD-018)."
            )
        if action == "accept_urgent":
            return IWDState.URGENT_PRIORITY_ACTIVE
        if action == "decline_urgent":
            return IWDState.ASSESSED  # Reverts to normal processing

    raise InvalidStateTransitionError(
        f"Invalid urgent transition from '{current_state.value}' with action '{action}' by '{actor_role}'."
    )

