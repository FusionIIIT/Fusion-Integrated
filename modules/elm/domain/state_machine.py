"""Pure Python State Machine for ELM Workflows.

Implements Authoritative State Transition Tables:
- CW-EL-01: New Leave Processing & Immediate Withdrawal
- CW-EL-02: Pre-Start Approved Leave Cancellation
- CW-EL-03: Ongoing Leave Extension
- CW-EL-04: Resumption Review & Balance Adjustments
Zero framework dependencies.
"""
from __future__ import annotations

from modules.elm.domain.entities import LeaveCategory, LeaveStatus, StateTransitionResult


class LeaveStateMachine:
    """Encapsulates valid state transitions and guard rules for ELM."""

    PENDING_STATUSES = {
        LeaveStatus.AWAITING_SUBSTITUTE,
        LeaveStatus.SUBSTITUTE_DECLINED,
        LeaveStatus.AWAITING_UNIT_HEAD,
        LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        LeaveStatus.AWAITING_ESTABLISHMENT,
        LeaveStatus.AWAITING_FINAL_SANCTION,
    }

    # -------------------------------------------------------------------------
    # CW-EL-01: New Leave Transitions
    # -------------------------------------------------------------------------
    @staticmethod
    def submit_application(
        requires_substitute: bool,
        is_director: bool,
    ) -> LeaveStatus:
        """STT Row 1-3: Draft -> Pending progression."""
        if requires_substitute:
            return LeaveStatus.AWAITING_SUBSTITUTE
        if is_director:
            return LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION
        return LeaveStatus.AWAITING_UNIT_HEAD

    @staticmethod
    def process_substitute_response(
        current_status: LeaveStatus,
        accepted: bool,
        is_director: bool,
    ) -> StateTransitionResult:
        """STT Row 4-6: Substitute response handling."""
        if current_status != LeaveStatus.AWAITING_SUBSTITUTE:
            return StateTransitionResult(False, current_status, "Request is not awaiting substitute.")

        if not accepted:
            return StateTransitionResult(
                True, LeaveStatus.SUBSTITUTE_DECLINED,
                "Substitute declined responsibility coverage."
            )

        next_status = (LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION
                       if is_director else LeaveStatus.AWAITING_UNIT_HEAD)
        return StateTransitionResult(True, next_status, "Substitute accepted responsibility.")

    @staticmethod
    def replace_substitute(current_status: LeaveStatus) -> StateTransitionResult:
        """STT Row 7: Replace substitute after decline."""
        if current_status != LeaveStatus.SUBSTITUTE_DECLINED:
            return StateTransitionResult(False, current_status, "No substitute decline to recover from.")
        return StateTransitionResult(
            True, LeaveStatus.AWAITING_SUBSTITUTE, "Replacement substitute nominated."
        )

    @staticmethod
    def unit_head_review(
        category: str,
        decision: str,  # "approve", "reject", "recommend", "not_recommend"
        has_establishment_step: bool = True,
    ) -> StateTransitionResult:
        """STT Row 8-11: Unit Head review outcome."""
        cat = category.upper()
        # Direct final decision for CL and RH (BR-EL-016)
        if cat in (LeaveCategory.CL.value, LeaveCategory.RH.value):
            if decision == "approve":
                return StateTransitionResult(True, LeaveStatus.APPROVED, "Approved by Unit Head.")
            if decision == "reject":
                return StateTransitionResult(True, LeaveStatus.REJECTED, "Rejected by Unit Head.")
            return StateTransitionResult(False, LeaveStatus.AWAITING_UNIT_HEAD,
                                         "CL/RH requires final approve or reject.")

        # Higher sanction leaves (SCL, EL, VL, COL) - BR-EL-017, BR-EL-018
        if decision not in ("recommend", "not_recommend"):
            return StateTransitionResult(
                False, LeaveStatus.AWAITING_UNIT_HEAD,
                "Higher sanction leaves require Recommended or Not Recommended."
            )

        if has_establishment_step:
            return StateTransitionResult(
                True, LeaveStatus.AWAITING_ESTABLISHMENT,
                f"Unit Head recorded {decision}; routed to Establishment."
            )
        return StateTransitionResult(
            True, LeaveStatus.AWAITING_FINAL_SANCTION,
            f"Unit Head recorded {decision}; routed to Sanctioning Authority."
        )

    @staticmethod
    def establishment_route() -> StateTransitionResult:
        """STT Row 12: Establishment verification and routing."""
        return StateTransitionResult(
            True, LeaveStatus.AWAITING_FINAL_SANCTION,
            "Establishment record check complete; forwarded to Competent Authority."
        )

    @staticmethod
    def final_sanction(approved: bool) -> StateTransitionResult:
        """STT Row 13-16: Final Sanction decision."""
        if approved:
            return StateTransitionResult(True, LeaveStatus.APPROVED, "Leave sanctioned.")
        return StateTransitionResult(True, LeaveStatus.REJECTED, "Leave rejected.")

    @staticmethod
    def withdraw_pending(current_status: LeaveStatus) -> StateTransitionResult:
        """STT Row 17: Immediate withdrawal of pending request (BR-EL-022)."""
        if current_status not in LeaveStateMachine.PENDING_STATUSES:
            return StateTransitionResult(
                False, current_status, "Only pending requests may be withdrawn."
            )
        return StateTransitionResult(
            True, LeaveStatus.WITHDRAWN, "Request successfully withdrawn immediately."
        )

    # -------------------------------------------------------------------------
    # CW-EL-02: Pre-Start Cancellation Transitions
    # -------------------------------------------------------------------------
    @staticmethod
    def request_cancellation(current_status: LeaveStatus) -> StateTransitionResult:
        """CW-EL-02 Row 1: Initiate cancellation on approved leave."""
        if current_status != LeaveStatus.APPROVED:
            return StateTransitionResult(
                False, current_status, "Only approved leave may be cancelled."
            )
        return StateTransitionResult(
            True, LeaveStatus.CANCELLATION_PENDING_UNIT_HEAD, "Cancellation request submitted."
        )

    @staticmethod
    def review_cancellation(
        category: str,
        approved: bool,
        current_status: LeaveStatus,
        has_establishment_step: bool = True,
    ) -> StateTransitionResult:
        """CW-EL-02 Row 2-8: Review cancellation."""
        cat = category.upper()
        if cat in (LeaveCategory.CL.value, LeaveCategory.RH.value):
            if approved:
                return StateTransitionResult(
                    True, LeaveStatus.CANCELLED, "Cancellation approved; balance restored."
                )
            return StateTransitionResult(
                True, LeaveStatus.APPROVED, "Cancellation rejected; original leave retained."
            )

        # Higher sanction path
        if current_status == LeaveStatus.CANCELLATION_PENDING_UNIT_HEAD:
            next_step = (LeaveStatus.CANCELLATION_PENDING_ESTABLISHMENT
                         if has_establishment_step else LeaveStatus.CANCELLATION_PENDING_FINAL)
            return StateTransitionResult(True, next_step, "Cancellation recommendation recorded.")

        if current_status == LeaveStatus.CANCELLATION_PENDING_ESTABLISHMENT:
            return StateTransitionResult(
                True, LeaveStatus.CANCELLATION_PENDING_FINAL, "Forwarded to Sanctioning Authority."
            )

        if current_status == LeaveStatus.CANCELLATION_PENDING_FINAL:
            if approved:
                return StateTransitionResult(
                    True, LeaveStatus.CANCELLED, "Cancellation approved; balance restored."
                )
            return StateTransitionResult(
                True, LeaveStatus.APPROVED, "Cancellation rejected; original leave retained."
            )

        return StateTransitionResult(False, current_status, "Invalid cancellation state.")
