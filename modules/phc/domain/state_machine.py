"""Pure Python state machines for PHC workflows.

Enforces:
- CW-PHC-01 / BW-PHC-01 / BW-PHC-02 (Reimbursement progression)
- CW-PHC-02 / BW-PHC-03 / BW-PHC-04 (Procurement requisition progression)
- PHC-BR-08, PHC-BR-10, PHC-BR-14
"""
from __future__ import annotations

from .entities import ReimbursementStatus, RequisitionStatus
from .errors import ClaimImmutableError, InvalidStateTransitionError, RequisitionNotApprovedError


class ReimbursementStateMachine:
    """Implements CW-PHC-01, BW-PHC-01, BW-PHC-02."""

    @staticmethod
    def transition_phc_review_forward(current_status: str) -> ReimbursementStatus:
        if current_status != ReimbursementStatus.PENDING_PHC_REVIEW.value:
            raise InvalidStateTransitionError(
                f"Cannot forward claim from state '{current_status}'. Expected '{ReimbursementStatus.PENDING_PHC_REVIEW.value}'."
            )
        return ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION

    @staticmethod
    def transition_accounts_verify(current_status: str) -> ReimbursementStatus:
        if current_status != ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value:
            raise InvalidStateTransitionError(
                f"Cannot verify claim from state '{current_status}'. Expected '{ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value}'."
            )
        return ReimbursementStatus.PENDING_SANCTION

    @staticmethod
    def transition_sanction_decision(current_status: str, approve: bool) -> ReimbursementStatus:
        if current_status != ReimbursementStatus.PENDING_SANCTION.value:
            raise InvalidStateTransitionError(
                f"Cannot sanction claim from state '{current_status}'. Expected '{ReimbursementStatus.PENDING_SANCTION.value}'."
            )
        return ReimbursementStatus.APPROVED_FOR_PAYMENT if approve else ReimbursementStatus.REJECTED

    @staticmethod
    def transition_payment_process(current_status: str) -> ReimbursementStatus:
        if current_status != ReimbursementStatus.APPROVED_FOR_PAYMENT.value:
            raise InvalidStateTransitionError(
                f"Cannot process payment for claim in state '{current_status}'. Expected '{ReimbursementStatus.APPROVED_FOR_PAYMENT.value}'."
            )
        return ReimbursementStatus.REIMBURSED

    @staticmethod
    def assert_can_modify(current_status: str) -> None:
        """PHC-BR-14: Submitted and rejected claims cannot be edited in-place."""
        raise ClaimImmutableError(
            "PHC-BR-14: A submitted or rejected claim cannot be modified or reopened in-place. "
            "A new claim must be submitted."
        )


class RequisitionStateMachine:
    """Implements CW-PHC-02, BW-PHC-03, BW-PHC-04."""

    @staticmethod
    def transition_decision(current_status: str, approve: bool) -> RequisitionStatus:
        if current_status != RequisitionStatus.PENDING_APPROVAL.value:
            raise InvalidStateTransitionError(
                f"Cannot decide requisition in state '{current_status}'. Expected '{RequisitionStatus.PENDING_APPROVAL.value}'."
            )
        return RequisitionStatus.APPROVED if approve else RequisitionStatus.REJECTED

    @staticmethod
    def transition_fulfill(current_status: str) -> RequisitionStatus:
        if current_status != RequisitionStatus.APPROVED.value:
            raise RequisitionNotApprovedError(
                f"PHC-BR-10: Cannot fulfill requisition in state '{current_status}'. Requisition must be Approved first."
            )
        return RequisitionStatus.FULFILLED
