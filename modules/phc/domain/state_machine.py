"""PHC domain: state machines for reimbursement claims and procurement
requisitions. Pure Python - no Django or DRF (enforced by importlinter).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Reimbursement claim states (BW-PHC-01, BW-PHC-02, CW-PHC-01)
# ---------------------------------------------------------------------------


class ReimbursementState:
    PENDING_PHC_REVIEW = "pending_phc_review"
    PENDING_ACCOUNTS = "pending_accounts_verification"
    PENDING_SANCTION = "pending_sanction"
    APPROVED_FOR_PAYMENT = "approved_for_payment"
    REIMBURSED = "reimbursed"
    REJECTED = "rejected"


# Valid forward transitions: (from_state, to_state) → actor_role_set
# PHC Staff and Accounts & Audit have no reject/return branch (PHC-BR-08, E1 of UC-15/19).
_REIMBURSEMENT_TRANSITIONS: dict[tuple[str, str], frozenset[str]] = {
    # Step 1: Employee submits → enforced at service layer, not here
    (ReimbursementState.PENDING_PHC_REVIEW, ReimbursementState.PENDING_ACCOUNTS): frozenset(
        {"phc_staff"}
    ),
    (ReimbursementState.PENDING_ACCOUNTS, ReimbursementState.PENDING_SANCTION): frozenset(
        {"accounts_audit"}
    ),
    (ReimbursementState.PENDING_SANCTION, ReimbursementState.APPROVED_FOR_PAYMENT): frozenset(
        {"approving_authority"}
    ),
    (ReimbursementState.PENDING_SANCTION, ReimbursementState.REJECTED): frozenset(
        {"approving_authority"}
    ),
    (ReimbursementState.APPROVED_FOR_PAYMENT, ReimbursementState.REIMBURSED): frozenset(
        {"accounts_audit"}
    ),
}

TERMINAL_REIMBURSEMENT_STATES = frozenset(
    {
        ReimbursementState.REIMBURSED,
        ReimbursementState.REJECTED,
    }
)


class InvalidClaimTransition(Exception):
    pass


def advance_claim(from_state: str, to_state: str, actor_role: str) -> None:
    """Validate a reimbursement-claim state transition.

    Raises InvalidClaimTransition with a human-readable message if the move
    is not permitted.  Does not touch the database.
    """
    allowed = _REIMBURSEMENT_TRANSITIONS.get((from_state, to_state))
    if allowed is None:
        raise InvalidClaimTransition(f"Transition {from_state!r} → {to_state!r} is not modelled.")
    if actor_role not in allowed:
        raise InvalidClaimTransition(
            f"Role {actor_role!r} may not drive {from_state!r} → {to_state!r}."
        )


# ---------------------------------------------------------------------------
# Procurement requisition states (BW-PHC-03, BW-PHC-04, CW-PHC-02)
# ---------------------------------------------------------------------------


class RequisitionState:
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"


_REQUISITION_TRANSITIONS: dict[tuple[str, str], frozenset[str]] = {
    (RequisitionState.PENDING_APPROVAL, RequisitionState.APPROVED): frozenset(
        {"approving_authority"}
    ),
    (RequisitionState.PENDING_APPROVAL, RequisitionState.REJECTED): frozenset(
        {"approving_authority"}
    ),
    (RequisitionState.APPROVED, RequisitionState.FULFILLED): frozenset({"phc_staff"}),
}

TERMINAL_REQUISITION_STATES = frozenset(
    {
        RequisitionState.REJECTED,
        RequisitionState.FULFILLED,
    }
)


class InvalidRequisitionTransition(Exception):
    pass


def advance_requisition(from_state: str, to_state: str, actor_role: str) -> None:
    """Validate a procurement-requisition state transition."""
    allowed = _REQUISITION_TRANSITIONS.get((from_state, to_state))
    if allowed is None:
        raise InvalidRequisitionTransition(
            f"Transition {from_state!r} → {to_state!r} is not modelled."
        )
    if actor_role not in allowed:
        raise InvalidRequisitionTransition(
            f"Role {actor_role!r} may not drive {from_state!r} → {to_state!r}."
        )
