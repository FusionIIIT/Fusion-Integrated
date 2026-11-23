"""Declarative state machine and transition guards for IWD (DIRECT_FINAL_v2)."""

from __future__ import annotations

from typing import Any


class IWDState:
    """Authoritative workflow states for the IWD module."""

    SUBMITTED = "Submitted"
    ASSIGNED = "Assigned"
    ASSESSED = "Assessed"

    LOW_COST_REVIEW_PENDING = "Low-Cost Review Pending"
    REJECTED_LOW_COST = "Rejected - Low-Cost"

    MID_RANGE_COMMITTEE_REVIEW_PENDING = "Mid-Range Committee Review Pending"
    DEPARTMENT_HEAD_REVIEW_PENDING = "Department Head Review Pending"
    DIRECTOR_REVIEW_PENDING_MID = "Director Review Pending (Mid-Range)"
    REJECTED_MID_RANGE = "Rejected - Mid-Range"

    DIRECTOR_REVIEW_PENDING_HIGH = "Director Review Pending (High-Cost)"
    BIDDING_AUTHORIZED = "Bidding Authorized"
    VENDOR_SELECTED = "Vendor/Contractor Selected"
    REJECTED_DIRECTOR_ROUTE = "Rejected - Director Route"

    ESTIMATE_APPROVED = "Estimate Approved"

    MATERIALS_ISSUED = "Materials Issued"
    PROCUREMENT_NEEDED_LOW = "Procurement Needed (Low)"
    PROCUREMENT_NEEDED_MID = "Procurement Needed (Mid)"
    MATERIALS_AVAILABLE = "Materials Available"

    READY_FOR_EXECUTION = "Ready for Execution"
    VERIFICATION_PENDING = "Verification Pending"
    REWORK_REQUIRED = "Rework Required"
    RESOLVED = "Resolved"

    AUDIT_PENDING = "Audit Pending"
    DIRECTOR_PAYMENT_APPROVAL_PENDING = "Director Payment Approval Pending"
    ACCOUNTS_SETTLEMENT_PENDING = "Accounts Settlement Pending"
    SETTLED = "Settled"

    URGENT_REVIEW_PENDING = "Urgent Review Pending"
    URGENT_PRIORITY_ACTIVE = "Urgent Priority Active"


TRANSITION_MAP: dict[str, dict[str, str]] = {
    # BW-IWD-01
    IWDState.SUBMITTED: {"assign": IWDState.ASSIGNED},
    IWDState.ASSIGNED: {"assess": IWDState.ASSESSED, "flag_urgent": IWDState.URGENT_REVIEW_PENDING},
    IWDState.ASSESSED: {
        "submit_low": IWDState.LOW_COST_REVIEW_PENDING,
        "submit_mid": IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING,
        "submit_high": IWDState.DIRECTOR_REVIEW_PENDING_HIGH,
        "flag_urgent": IWDState.URGENT_REVIEW_PENDING,
    },
    # BW-IWD-02, BW-IWD-12
    IWDState.LOW_COST_REVIEW_PENDING: {
        "approve": IWDState.ESTIMATE_APPROVED,
        "reject": IWDState.REJECTED_LOW_COST,
    },
    IWDState.REJECTED_LOW_COST: {"modify_resubmit": IWDState.LOW_COST_REVIEW_PENDING},
    # BW-IWD-03, BW-IWD-04, BW-IWD-13
    IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING: {
        "record_committee": IWDState.DEPARTMENT_HEAD_REVIEW_PENDING,
    },
    IWDState.DEPARTMENT_HEAD_REVIEW_PENDING: {
        "approve": IWDState.ESTIMATE_APPROVED,
        "reject": IWDState.REJECTED_MID_RANGE,
        "forward": IWDState.DIRECTOR_REVIEW_PENDING_MID,
    },
    IWDState.DIRECTOR_REVIEW_PENDING_MID: {
        "approve": IWDState.ESTIMATE_APPROVED,
        "reject": IWDState.REJECTED_DIRECTOR_ROUTE,
    },
    IWDState.REJECTED_MID_RANGE: {
        "modify_resubmit": IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING,
    },
    # BW-IWD-05, BW-IWD-14
    IWDState.DIRECTOR_REVIEW_PENDING_HIGH: {
        "approve": IWDState.BIDDING_AUTHORIZED,
        "reject": IWDState.REJECTED_DIRECTOR_ROUTE,
    },
    IWDState.BIDDING_AUTHORIZED: {"select_vendor": IWDState.VENDOR_SELECTED},
    IWDState.VENDOR_SELECTED: {"finalize_vendor": IWDState.READY_FOR_EXECUTION},
    IWDState.REJECTED_DIRECTOR_ROUTE: {
        "modify_resubmit": IWDState.DIRECTOR_REVIEW_PENDING_HIGH,
    },
    # BW-IWD-06, BW-IWD-07, BW-IWD-08
    IWDState.ESTIMATE_APPROVED: {
        "issue_stock": IWDState.MATERIALS_ISSUED,
        "shortage_low": IWDState.PROCUREMENT_NEEDED_LOW,
        "shortage_mid": IWDState.PROCUREMENT_NEEDED_MID,
    },
    IWDState.PROCUREMENT_NEEDED_LOW: {"procure_complete": IWDState.MATERIALS_AVAILABLE},
    IWDState.PROCUREMENT_NEEDED_MID: {"procure_complete": IWDState.MATERIALS_AVAILABLE},
    IWDState.MATERIALS_AVAILABLE: {"issue_stock": IWDState.MATERIALS_ISSUED},
    IWDState.MATERIALS_ISSUED: {"start_execution": IWDState.READY_FOR_EXECUTION},
    # BW-IWD-09, BW-IWD-10
    IWDState.READY_FOR_EXECUTION: {"work_complete": IWDState.VERIFICATION_PENDING},
    IWDState.VERIFICATION_PENDING: {
        "verify_approved": IWDState.RESOLVED,
        "verify_rework": IWDState.REWORK_REQUIRED,
    },
    IWDState.REWORK_REQUIRED: {"rework_complete": IWDState.VERIFICATION_PENDING},
    # BW-IWD-11
    IWDState.RESOLVED: {"submit_bill": IWDState.AUDIT_PENDING},
    IWDState.AUDIT_PENDING: {
        "audit_validate": IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING,
        "audit_query": IWDState.AUDIT_PENDING,
    },
    IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING: {
        "director_approve_payment": IWDState.ACCOUNTS_SETTLEMENT_PENDING,
    },
    IWDState.ACCOUNTS_SETTLEMENT_PENDING: {"accounts_settle": IWDState.SETTLED},
    # BW-IWD-15
    IWDState.URGENT_REVIEW_PENDING: {
        "accept_fast_track": IWDState.URGENT_PRIORITY_ACTIVE,
        "decline_fast_track": IWDState.ASSESSED,
    },
}


class InvalidStateTransitionError(Exception):
    """Raised when an action is not permitted from the current workflow state."""


class RoleSeparationViolationError(Exception):
    """Raised when Dean attempts to act in Department Head capacity (BR-IWD-018)."""


def get_next_state(
    current_state: str, action: str, actor_role: str, context: dict[str, Any] | None = None
) -> str:
    """Validate and transition to next state, enforcing business rules and role separation."""
    ctx = context or {}

    # BR-IWD-018: Strict separation of Department Head and Dean
    if actor_role == "iwd_dean" and action in [
        "approve",
        "reject",
        "forward",
        "verify_approved",
        "verify_rework",
    ]:
        msg = (
            "BR-IWD-018: Department Head and Dean are distinct approval roles; "
            "Dean cannot perform Department Head transitions."
        )
        raise RoleSeparationViolationError(msg)

    # BR-IWD-014, BW-IWD-10: Max 1 rework traversal guard
    if action == "verify_rework" and ctx.get("rework_count", 0) >= 1:
        msg = "BW-IWD-10: Only one rework traversal is permitted; maximum attempts exceeded."
        raise InvalidStateTransitionError(msg)

    transitions = TRANSITION_MAP.get(current_state, {})
    if action not in transitions:
        msg = f"Cannot perform action '{action}' from state '{current_state}'."
        raise InvalidStateTransitionError(msg)

    return transitions[action]
