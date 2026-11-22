"""(state, event, permission) -> state tables: claims CW-PHC-01, requisitions CW-PHC-02."""
from __future__ import annotations

from dataclasses import dataclass


class IllegalTransition(Exception):
    pass


@dataclass(frozen=True)
class Transition:
    source: str
    event: str
    permission: str
    target: str


class ClaimStatus:
    PENDING_PHC_REVIEW = "pending_phc_review"
    PENDING_ACCOUNTS = "pending_accounts_verification"
    PENDING_SANCTION = "pending_sanction"
    APPROVED_FOR_PAYMENT = "approved_for_payment"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"

    CHOICES = (
        (PENDING_PHC_REVIEW, "Pending PHC review"),
        (PENDING_ACCOUNTS, "Pending Accounts verification"),
        (PENDING_SANCTION, "Pending sanction"),
        (APPROVED_FOR_PAYMENT, "Approved for payment"),
        (REJECTED, "Rejected"),
        (REIMBURSED, "Reimbursed"),
    )
    TERMINAL = frozenset({REJECTED, REIMBURSED})


class RequisitionStatus:
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"

    CHOICES = (
        (PENDING_APPROVAL, "Pending approval"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (FULFILLED, "Fulfilled"),
    )
    TERMINAL = frozenset({REJECTED, FULFILLED})


P_CLAIM_REVIEW = "phc.claim.review"
P_CLAIM_UPDATE = "phc.claim.update"
P_CLAIM_APPROVE = "phc.claim.approve"
P_REQUISITION_APPROVE = "phc.requisition.approve"
P_REQUISITION_UPDATE = "phc.requisition.update"

# PHC-BR-08: PHC Staff -> Accounts & Audit -> Approving Authority -> Accounts & Audit.
CLAIM_TRANSITIONS = (
    Transition(ClaimStatus.PENDING_PHC_REVIEW, "forward", P_CLAIM_REVIEW,
               ClaimStatus.PENDING_ACCOUNTS),
    Transition(ClaimStatus.PENDING_ACCOUNTS, "verify", P_CLAIM_UPDATE,
               ClaimStatus.PENDING_SANCTION),
    Transition(ClaimStatus.PENDING_SANCTION, "approve", P_CLAIM_APPROVE,
               ClaimStatus.APPROVED_FOR_PAYMENT),
    Transition(ClaimStatus.PENDING_SANCTION, "reject", P_CLAIM_APPROVE,
               ClaimStatus.REJECTED),
    Transition(ClaimStatus.APPROVED_FOR_PAYMENT, "pay", P_CLAIM_UPDATE,
               ClaimStatus.REIMBURSED),
)

# PHC-BR-10: nothing proceeds to fulfilment without an approval.
REQUISITION_TRANSITIONS = (
    Transition(RequisitionStatus.PENDING_APPROVAL, "approve", P_REQUISITION_APPROVE,
               RequisitionStatus.APPROVED),
    Transition(RequisitionStatus.PENDING_APPROVAL, "reject", P_REQUISITION_APPROVE,
               RequisitionStatus.REJECTED),
    Transition(RequisitionStatus.APPROVED, "fulfill", P_REQUISITION_UPDATE,
               RequisitionStatus.FULFILLED),
)

CLAIM_EVENTS = frozenset(t.event for t in CLAIM_TRANSITIONS)
REQUISITION_EVENTS = frozenset(t.event for t in REQUISITION_TRANSITIONS)


def resolve(table: tuple[Transition, ...], source: str, event: str,
            permissions: frozenset[str] | set[str]) -> Transition:
    for row in table:
        if row.source == source and row.event == event and row.permission in permissions:
            return row
    raise IllegalTransition(f"{event} is not allowed from {source}.")


def events_for(table: tuple[Transition, ...], source: str,
               permissions: frozenset[str] | set[str]) -> list[str]:
    return [row.event for row in table
            if row.source == source and row.permission in permissions]
