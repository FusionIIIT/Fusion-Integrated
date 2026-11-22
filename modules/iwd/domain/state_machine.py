from dataclasses import dataclass
from typing import Mapping, Tuple

State = str
Event = str
Role = str

TransitionKey = Tuple[State, Event, Role]


@dataclass(frozen=True)
class TransitionOutcome:
    next_state: str
    allowed: bool
    reason: str = ""


# Immutable declarative transition map: (current_state, event, acting_role) -> next_state
TRANSITIONS: Mapping[TransitionKey, str] = {
    # 1. Intake and Assessment
    ("submitted", "assign_engineer", "system"): "assigned",
    ("assigned", "record_assessment", "engineer"): "assessed",

    # 2. Estimate Routing (BR-IWD-003)
    ("assessed", "submit_estimate_low", "engineer"): "low_cost_review_pending",
    ("assessed", "submit_estimate_mid", "engineer"): "mid_range_committee_pending",
    ("assessed", "submit_estimate_high", "engineer"): "director_review_high_pending",

    # 3. Low-Cost Approval (BR-IWD-004)
    ("low_cost_review_pending", "approve_low_cost", "iwd_admin"): "estimate_approved",
    ("low_cost_review_pending", "reject_low_cost", "iwd_admin"): "rejected_low_cost",

    # 4. Mid-Range Approval (BR-IWD-005, BR-IWD-006)
    ("mid_range_committee_pending", "record_committee_review", "review_committee"): "dept_head_review_pending",
    ("dept_head_review_pending", "approve_dept_head", "department_head"): "estimate_approved",
    ("dept_head_review_pending", "forward_to_director", "department_head"): "director_review_mid_pending",
    ("dept_head_review_pending", "reject_dept_head", "department_head"): "rejected_mid_range",
    ("director_review_mid_pending", "approve_director_mid", "director"): "estimate_approved",
    ("director_review_mid_pending", "reject_director_mid", "director"): "rejected_director_route",

    # 5. High-Cost Approval and Bidding (BR-IWD-007, BR-IWD-008)
    ("director_review_high_pending", "authorize_bidding", "director"): "bidding_authorized",
    ("director_review_high_pending", "reject_director_high", "director"): "rejected_director_route",
    ("bidding_authorized", "select_vendor", "iwd_admin"): "vendor_selected",
    ("vendor_selected", "confirm_procurement", "iwd_admin"): "estimate_approved",

    # 6. Inventory & Procurement (BR-IWD-010)
    ("estimate_approved", "issue_materials_direct", "iwd_admin"): "ready_for_execution",
    ("estimate_approved", "flag_procurement_low", "iwd_admin"): "procurement_needed_low",
    ("estimate_approved", "flag_procurement_mid", "iwd_admin"): "procurement_needed_mid",
    ("procurement_needed_low", "complete_procurement", "iwd_admin"): "materials_available",
    ("procurement_needed_mid", "complete_procurement", "iwd_admin"): "materials_available",
    ("materials_available", "issue_materials", "iwd_admin"): "ready_for_execution",

    # 7. Work Execution, Verification & Rework (BR-IWD-014)
    ("ready_for_execution", "complete_work", "engineer"): "verification_pending",
    ("verification_pending", "verify_approved", "department_head"): "resolved",
    ("verification_pending", "verify_rework", "department_head"): "rework_required",
    ("rework_required", "complete_work", "engineer"): "verification_pending",

    # 8. Billing, Audit, Settlement (BR-IWD-015, BR-IWD-016)
    ("resolved", "submit_final_bill", "engineer"): "audit_pending",
    ("audit_pending", "audit_validated", "auditor"): "director_payment_approval_pending",
    ("director_payment_approval_pending", "approve_payment", "director"): "accounts_settlement_pending",
    ("accounts_settlement_pending", "record_settlement", "accounts"): "settled",

    # 9. Rejections and Resubmissions (BR-IWD-009)
    ("rejected_low_cost", "resubmit_estimate", "engineer"): "low_cost_review_pending",
    ("rejected_mid_range", "resubmit_estimate", "engineer"): "mid_range_committee_pending",
    ("rejected_director_route", "resubmit_estimate", "engineer"): "director_review_high_pending",
}


def transition(current_state: str, event: str, role: str) -> TransitionOutcome:
    """Evaluates state transition against declarative matrix."""
    key = (current_state, event, role)
    if key in TRANSITIONS:
        return TransitionOutcome(next_state=TRANSITIONS[key], allowed=True)
    return TransitionOutcome(
        next_state=current_state,
        allowed=False,
        reason=f"Transition from '{current_state}' via '{event}' by role '{role}' is illegal.",
    )
