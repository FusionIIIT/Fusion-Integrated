"""Forward-only claim and requisition transitions (PHC-BR-08, PHC-BR-10, PHC-BR-14)."""
from __future__ import annotations

from typing import Any

CLAIM_STATES = (
    "submitted", "pending_audit", "pending_sanction",
    "approved_for_payment", "reimbursed", "rejected",
)
CLAIM_TRANSITIONS = {
    "submitted": frozenset({"pending_audit"}),
    "pending_audit": frozenset({"pending_sanction"}),
    "pending_sanction": frozenset({"approved_for_payment", "rejected"}),
    "approved_for_payment": frozenset({"reimbursed"}),
    "reimbursed": frozenset(),
    "rejected": frozenset(),
}
CLAIM_ACTION_TARGETS = {
    "review": "pending_audit",
    "verify": "pending_sanction",
    "sanction_approve": "approved_for_payment",
    "sanction_reject": "rejected",
    "payment": "reimbursed",
}
CLAIM_EXPECTED = {
    "review": "submitted", "verify": "pending_audit",
    "sanction_approve": "pending_sanction", "sanction_reject": "pending_sanction",
    "payment": "approved_for_payment",
}

REQUISITION_STATES = ("pending_approval", "approved", "rejected", "fulfilled")
REQUISITION_TRANSITIONS = {
    "pending_approval": frozenset({"approved", "rejected"}),
    "approved": frozenset({"fulfilled"}),
    "rejected": frozenset(),
    "fulfilled": frozenset(),
}
REQUISITION_ACTION_TARGETS = {
    "approve": "approved", "reject": "rejected", "fulfill": "fulfilled",
}
REQUISITION_EXPECTED = {"approve": "pending_approval",
                        "reject": "pending_approval",
                        "fulfill": "approved"}

# A row past the expected stage means the action already happened. Rejection is
# deliberately not a conflict: it ends the workflow, so no later action applies.
CLAIM_DONE_STATES = {
    "review": frozenset({"pending_audit", "pending_sanction",
                         "approved_for_payment", "reimbursed"}),
    "verify": frozenset({"pending_sanction", "approved_for_payment", "reimbursed"}),
    "sanction_approve": frozenset({"approved_for_payment", "reimbursed"}),
    "sanction_reject": frozenset({"approved_for_payment", "reimbursed"}),
    "payment": frozenset({"reimbursed"}),
}
REQUISITION_DONE_STATES = {
    "approve": frozenset({"approved", "fulfilled"}),
    "reject": frozenset({"approved", "fulfilled"}),
    "fulfill": frozenset({"fulfilled"}),
}


class InvalidTransition(ValueError):
    """Raised when an action is not defined for a state. Pure, not an HTTP error."""


def next_claim_state(current: Any, action: str) -> str:
    """Return the target state for a claim action, or raise InvalidTransition."""
    target = CLAIM_ACTION_TARGETS.get(action)
    if target is None:
        raise InvalidTransition(f"Unknown claim action {action!r}.")
    if target not in CLAIM_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransition(f"Cannot {action} a claim in state {current!r}.")
    return target


def next_requisition_state(current: Any, action: str) -> str:
    """Return the target state for a requisition action, or raise InvalidTransition."""
    target = REQUISITION_ACTION_TARGETS.get(action)
    if target is None:
        raise InvalidTransition(f"Unknown requisition action {action!r}.")
    if target not in REQUISITION_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransition(f"Cannot {action} a requisition in state {current!r}.")
    return target
