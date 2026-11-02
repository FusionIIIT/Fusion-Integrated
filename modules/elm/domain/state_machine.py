"""Pure Python State Machine for ELM Workflows.

Implements authoritatively:
- New Leave Application & Progression (Draft -> Substitute -> Unit Head -> Sanction Authority -> Approved/Rejected)
- Pre-Start Cancellation of Approved Leave
- Duty Resumption after Leave
- Withdrawal of Pending Leave Requests

Zero external framework dependencies.
"""
from __future__ import annotations

from datetime import date

from modules.elm.domain.entities import LeaveStatus, StateTransitionResult


class LeaveStateMachine:
    """Encapsulates valid state transitions and guard rules for ELM."""

    TERMINAL_STATUSES = {
        LeaveStatus.APPROVED,
        LeaveStatus.REJECTED,
        LeaveStatus.WITHDRAWN,
        LeaveStatus.CANCELLED,
        LeaveStatus.RESUMED,
    }

    PENDING_STATUSES = {
        LeaveStatus.AWAITING_SUBSTITUTE,
        LeaveStatus.SUBSTITUTE_DECLINED,
        LeaveStatus.AWAITING_UNIT_HEAD,
        LeaveStatus.AWAITING_SANCTION,
    }

    @staticmethod
    def submit_application(requires_substitute: bool) -> LeaveStatus:
        """Determines the initial workflow state upon submission."""
        if requires_substitute:
            return LeaveStatus.AWAITING_SUBSTITUTE
        return LeaveStatus.AWAITING_UNIT_HEAD

    @staticmethod
    def process_substitute_response(
        current_status: LeaveStatus,
        accepted: bool,
    ) -> StateTransitionResult:
        """Substitute response transition guard and resolution."""
        if current_status != LeaveStatus.AWAITING_SUBSTITUTE:
            return StateTransitionResult(
                is_valid=False,
                next_status=current_status,
                message="Request is not awaiting substitute response.",
            )

        if not accepted:
            return StateTransitionResult(
                is_valid=True,
                next_status=LeaveStatus.SUBSTITUTE_DECLINED,
                message="Substitute declined responsibility coverage.",
            )

        return StateTransitionResult(
            is_valid=True,
            next_status=LeaveStatus.AWAITING_UNIT_HEAD,
            message="Substitute accepted. Routed to Unit Head for review.",
        )

    @staticmethod
    def process_unit_head_review(
        current_status: LeaveStatus,
        recommended: bool,
    ) -> StateTransitionResult:
        """Unit Head review transition guard and resolution."""
        if current_status != LeaveStatus.AWAITING_UNIT_HEAD:
            return StateTransitionResult(
                is_valid=False,
                next_status=current_status,
                message="Request is not in Unit Head review stage.",
            )

        if not recommended:
            return StateTransitionResult(
                is_valid=True,
                next_status=LeaveStatus.REJECTED,
                message="Unit Head rejected the application.",
            )

        return StateTransitionResult(
            is_valid=True,
            next_status=LeaveStatus.AWAITING_SANCTION,
            message="Unit Head recommended. Routed to Sanctioning Authority.",
        )

    @staticmethod
    def process_sanction_decision(
        current_status: LeaveStatus,
        approved: bool,
    ) -> StateTransitionResult:
        """Sanction decision transition guard and resolution."""
        if current_status != LeaveStatus.AWAITING_SANCTION:
            return StateTransitionResult(
                is_valid=False,
                next_status=current_status,
                message="Request is not awaiting sanction decision.",
            )

        if not approved:
            return StateTransitionResult(
                is_valid=True,
                next_status=LeaveStatus.REJECTED,
                message="Sanctioning Authority rejected the leave request.",
            )

        return StateTransitionResult(
            is_valid=True,
            next_status=LeaveStatus.APPROVED,
            message="Leave application approved and sanctioned.",
        )

    @staticmethod
    def withdraw(current_status: LeaveStatus) -> StateTransitionResult:
        """Allows employee to withdraw any pending request before final decision."""
        if current_status in LeaveStateMachine.TERMINAL_STATUSES:
            return StateTransitionResult(
                is_valid=False,
                next_status=current_status,
                message=f"Cannot withdraw a request that is already in terminal state '{current_status.value}'.",
            )

        return StateTransitionResult(
            is_valid=True,
            next_status=LeaveStatus.WITHDRAWN,
            message="Leave request withdrawn by applicant.",
        )

    @staticmethod
    def cancel_approved_leave(
        current_status: LeaveStatus,
        start_date: date,
        today: date,
    ) -> StateTransitionResult:
        """Pre-start cancellation: Employee may cancel approved leave on or before start_date."""
        if current_status != LeaveStatus.APPROVED:
            return StateTransitionResult(
                is_valid=False,
                next_status=current_status,
                message="Only approved leaves can be cancelled.",
            )

        if today > start_date:
            return StateTransitionResult(
                is_valid=False,
                next_status=current_status,
                message="Leave has already commenced. Post-start cancellation is not permitted.",
            )

        return StateTransitionResult(
            is_valid=True,
            next_status=LeaveStatus.CANCELLED,
            message="Approved leave cancelled prior to start date.",
        )

    @staticmethod
    def submit_resumption(current_status: LeaveStatus) -> StateTransitionResult:
        """Duty resumption: Submitted after completion of approved leave."""
        if current_status != LeaveStatus.APPROVED:
            return StateTransitionResult(
                is_valid=False,
                next_status=current_status,
                message="Duty resumption can only be recorded for approved leaves.",
            )

        return StateTransitionResult(
            is_valid=True,
            next_status=LeaveStatus.RESUMED,
            message="Duty resumption confirmed.",
        )
