"""State machine for Employee Leave Management workflows.

Pure Python — no Django, DRF or Celery imports permitted.
Implements:
- CW-EL-01: New Leave Processing and Pending Withdrawal
- CW-EL-02: Approved Leave Cancellation
- CW-EL-03: Ongoing Leave Extension
- CW-EL-04: Resumption Review
"""
from typing import Optional

from modules.leave.domain.constants import (
    LeaveCategory,
    LeaveStatus,
    SubstituteStatus,
    UnitHeadDecision,
)


def get_initial_status(
    has_substitute: bool,
    is_director: bool = False,
) -> LeaveStatus:
    """Determine initial status upon submission.

    - If substitute required: PENDING_SUBSTITUTE
    - If no substitute required:
      - If Director: APPROVED (self-sanction per BR-EL-020)
      - Else: PENDING_UNIT_HEAD
    """
    if has_substitute:
        return LeaveStatus.PENDING_SUBSTITUTE
    if is_director:
        return LeaveStatus.APPROVED
    return LeaveStatus.PENDING_UNIT_HEAD


def transition_on_substitute_response(
    current_status: LeaveStatus,
    substitute_response: SubstituteStatus,
    is_director: bool = False,
) -> LeaveStatus:
    """Transition when substitute accepts or declines (CW-EL-01, BR-EL-015)."""
    if current_status != LeaveStatus.PENDING_SUBSTITUTE:
        raise ValueError(f"Cannot process substitute response from status {current_status.value}")

    if substitute_response == SubstituteStatus.ACCEPTED:
        return LeaveStatus.APPROVED if is_director else LeaveStatus.PENDING_UNIT_HEAD
    elif substitute_response == SubstituteStatus.DECLINED:
        return LeaveStatus.SUBSTITUTE_DECLINED
    raise ValueError(f"Invalid substitute response: {substitute_response}")


def transition_on_unit_head_review(
    current_status: LeaveStatus,
    category: str | LeaveCategory,
    decision: UnitHeadDecision,
) -> LeaveStatus:
    """Transition when Unit Head reviews request (BR-EL-016, BR-EL-017).

    - For CL and RH: Unit Head is final authority.
      - APPROVE -> APPROVED
      - REJECT -> REJECTED
    - For SCL, EL, COL, VL: Unit Head records Recommendation.
      - RECOMMENDED or NOT_RECOMMENDED -> PENDING_SANCTION
    """
    if current_status not in (LeaveStatus.PENDING_UNIT_HEAD, LeaveStatus.CANCEL_REQUESTED):
        raise ValueError(f"Unit head review not permitted for status {current_status.value}")

    cat = LeaveCategory(category)
    is_cl_rh = cat in (LeaveCategory.CL, LeaveCategory.RH)

    # If it is a cancellation request
    if current_status == LeaveStatus.CANCEL_REQUESTED:
        if is_cl_rh:
            return LeaveStatus.CANCELLED if decision == UnitHeadDecision.APPROVE else LeaveStatus.APPROVED
        else:
            # Advance cancellation to higher sanction
            return LeaveStatus.CANCEL_REQUESTED

    # Normal request
    if is_cl_rh:
        if decision == UnitHeadDecision.APPROVE:
            return LeaveStatus.APPROVED
        elif decision == UnitHeadDecision.REJECT:
            return LeaveStatus.REJECTED
        else:
            raise ValueError(f"CL/RH requires final APPROVE or REJECT from Unit Head, got {decision.value}")
    else:
        # SCL, EL, COL, VL: Recommendation forwards to higher sanction
        if decision in (UnitHeadDecision.RECOMMENDED, UnitHeadDecision.NOT_RECOMMENDED):
            return LeaveStatus.PENDING_SANCTION
        raise ValueError(f"Higher-sanction category {cat.value} requires recommendation, got {decision.value}")


def transition_on_sanction_decision(
    current_status: LeaveStatus,
    is_cancellation: bool,
    approved: bool,
) -> LeaveStatus:
    """Transition when final Sanctioning Authority makes a decision (BR-EL-018)."""
    if is_cancellation:
        if current_status != LeaveStatus.CANCEL_REQUESTED:
            raise ValueError(f"Cannot process cancellation sanction from status {current_status.value}")
        return LeaveStatus.CANCELLED if approved else LeaveStatus.APPROVED

    if current_status != LeaveStatus.PENDING_SANCTION:
        raise ValueError(f"Sanction decision not permitted from status {current_status.value}")
    return LeaveStatus.APPROVED if approved else LeaveStatus.REJECTED


def can_withdraw(status: LeaveStatus) -> bool:
    """Check if request can be withdrawn (BR-EL-022, BR-EL-034).

    Available on any pending request before final approval.
    """
    pending_statuses = {
        LeaveStatus.DRAFT,
        LeaveStatus.PENDING_SUBSTITUTE,
        LeaveStatus.SUBSTITUTE_DECLINED,
        LeaveStatus.PENDING_UNIT_HEAD,
        LeaveStatus.PENDING_ESTABLISHMENT,
        LeaveStatus.PENDING_SANCTION,
    }
    return status in pending_statuses


def can_cancel_pre_start(status: LeaveStatus, start_date, current_date) -> bool:
    """Check if approved leave can be cancelled before start date (BR-EL-023)."""
    return status == LeaveStatus.APPROVED and current_date < start_date


def can_extend(status: LeaveStatus, category: str | LeaveCategory, start_date, end_date, current_date) -> bool:
    """Check if ongoing leave can be extended (BR-EL-025).

    Only ongoing EL, COL, or VL can be extended.
    """
    cat = LeaveCategory(category)
    is_ongoing_type = cat in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL)
    is_ongoing_period = start_date <= current_date <= end_date
    return status == LeaveStatus.APPROVED and is_ongoing_type and is_ongoing_period


def can_resume(status: LeaveStatus, category: str | LeaveCategory) -> bool:
    """Check if resumption can be submitted (BR-EL-027).

    Supported for approved EL, COL, and VL after completion/return.
    """
    cat = LeaveCategory(category)
    return status == LeaveStatus.APPROVED and cat in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL)
