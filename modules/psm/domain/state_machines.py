"""Declarative state machine definitions for PSM domain entities.

State transitions are modeled as (current_state, event, role) -> next_state mappings.
Illegal transitions are rejected with DomainTransitionError.
"""
from typing import NamedTuple


class TransitionKey(NamedTuple):
    current_state: str
    event: str
    role: str


class DomainTransitionError(Exception):
    def __init__(self, current_state: str, event: str, role: str):
        super().__init__(
            f"Cannot execute event '{event}' on state '{current_state}' with role '{role}'."
        )
        self.current_state = current_state
        self.event = event
        self.role = role


INDENT_TRANSITIONS: dict[TransitionKey, str] = {
    TransitionKey("DRAFT", "SUBMIT", "requestor"): "SUBMITTED",
    TransitionKey("DRAFT", "CANCEL", "requestor"): "CANCELLED",
    TransitionKey("SUBMITTED", "DEPT_VERIFY", "dept_admin"): "PENDING_DEPT_APPROVAL",
    TransitionKey("SUBMITTED", "HOD_APPROVE_LOW", "hod"): "PENDING_PS_REVIEW",
    TransitionKey("SUBMITTED", "HOD_REJECT", "hod"): "REJECTED",
    TransitionKey("SUBMITTED", "CANCEL", "requestor"): "CANCELLED",
    TransitionKey("PENDING_DEPT_APPROVAL", "HOD_APPROVE_LOW", "hod"): "PENDING_PS_REVIEW",
    TransitionKey("PENDING_DEPT_APPROVAL", "HOD_REJECT", "hod"): "REJECTED",
    TransitionKey("PENDING_PS_REVIEW", "PS_APPROVE_STANDARD", "ps_admin"): "APPROVED",
    TransitionKey(
        "PENDING_PS_REVIEW", "PS_ESCALATE_HIGH_VALUE", "ps_admin"
    ): "PENDING_DIRECTOR_APPROVAL",
    TransitionKey("PENDING_PS_REVIEW", "PS_REJECT", "ps_admin"): "REJECTED",
    TransitionKey("PENDING_DIRECTOR_APPROVAL", "DIRECTOR_APPROVE", "director"): "APPROVED",
    TransitionKey("PENDING_DIRECTOR_APPROVAL", "DIRECTOR_REJECT", "director"): "REJECTED",
    TransitionKey("APPROVED", "FULFILL_STOCK", "store_keeper"): "FULFILLED",
    TransitionKey("APPROVED", "ISSUE_PO", "purchase_officer"): "FULFILLED",
}

PO_TRANSITIONS: dict[TransitionKey, str] = {
    TransitionKey("DRAFT", "ISSUE", "purchase_officer"): "ISSUED",
    TransitionKey("ISSUED", "RECORD_DELIVERY_PARTIAL", "store_keeper"): "PARTIALLY_DELIVERED",
    TransitionKey("ISSUED", "RECORD_DELIVERY_COMPLETE", "store_keeper"): "COMPLETED",
    TransitionKey("PARTIALLY_DELIVERED", "RECORD_DELIVERY_COMPLETE", "store_keeper"): "COMPLETED",
    TransitionKey("ISSUED", "CANCEL", "purchase_officer"): "CANCELLED",
}

GRN_TRANSITIONS: dict[TransitionKey, str] = {
    TransitionKey("INSPECTION_PENDING", "ACCEPT_ALL", "store_keeper"): "ACCEPTED",
    TransitionKey("INSPECTION_PENDING", "FLAG_DISCREPANCY", "store_keeper"): "DISCREPANT",
    TransitionKey("DISCREPANT", "RESOLVE_DISCREPANCY", "purchase_officer"): "CLOSED",
    TransitionKey("ACCEPTED", "INDENTOR_CONFIRM", "requestor"): "CLOSED",
}

DISCREPANCY_TRANSITIONS: dict[TransitionKey, str] = {
    TransitionKey("OPEN_HOLD_PAYMENT", "RESOLVE", "purchase_officer"): "RESOLVED",
}


def can_transition_indent(current_state: str, event: str, role: str) -> bool:
    return TransitionKey(current_state, event, role) in INDENT_TRANSITIONS


def transition_indent(current_state: str, event: str, role: str) -> str:
    key = TransitionKey(current_state, event, role)
    if key not in INDENT_TRANSITIONS:
        raise DomainTransitionError(current_state, event, role)
    return INDENT_TRANSITIONS[key]


def can_transition_po(current_state: str, event: str, role: str) -> bool:
    return TransitionKey(current_state, event, role) in PO_TRANSITIONS


def transition_po(current_state: str, event: str, role: str) -> str:
    key = TransitionKey(current_state, event, role)
    if key not in PO_TRANSITIONS:
        raise DomainTransitionError(current_state, event, role)
    return PO_TRANSITIONS[key]


def can_transition_grn(current_state: str, event: str, role: str) -> bool:
    return TransitionKey(current_state, event, role) in GRN_TRANSITIONS


def transition_grn(current_state: str, event: str, role: str) -> str:
    key = TransitionKey(current_state, event, role)
    if key not in GRN_TRANSITIONS:
        raise DomainTransitionError(current_state, event, role)
    return GRN_TRANSITIONS[key]


def can_transition_discrepancy(current_state: str, event: str, role: str) -> bool:
    return TransitionKey(current_state, event, role) in DISCREPANCY_TRANSITIONS


def transition_discrepancy(current_state: str, event: str, role: str) -> str:
    key = TransitionKey(current_state, event, role)
    if key not in DISCREPANCY_TRANSITIONS:
        raise DomainTransitionError(current_state, event, role)
    return DISCREPANCY_TRANSITIONS[key]
