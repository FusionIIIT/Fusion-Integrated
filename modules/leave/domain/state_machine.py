"""Declarative state machine for leave workflows."""

from __future__ import annotations

from .errors import InvalidLeaveTransitionError


class LeaveState:
    DRAFT = "draft"
    SUBMITTED_PENDING_SUBSTITUTE = "submitted_pending_substitute"
    SUBSTITUTE_DECLINED = "substitute_declined"
    PENDING_REVIEW = "pending_review"
    PENDING_ROUTING = "pending_routing"
    PENDING_SANCTION = "pending_sanction"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    CANCELLATION_PENDING_REVIEW = "cancellation_pending_review"
    CANCELLATION_PENDING_ROUTING = "cancellation_pending_routing"
    CANCELLATION_PENDING_SANCTION = "cancellation_pending_sanction"
    CANCELLED = "cancelled"

    EXTENSION_PENDING_SUBSTITUTE = "extension_pending_substitute"
    EXTENSION_SUBSTITUTE_DECLINED = "extension_substitute_declined"
    EXTENSION_PENDING_REVIEW = "extension_pending_review"
    EXTENSION_PENDING_ROUTING = "extension_pending_routing"
    EXTENSION_PENDING_SANCTION = "extension_pending_sanction"

    RESUMPTION_PENDING = "resumption_pending"
    CLOSED = "closed"


TERMINAL_STATES: set[str] = {
    LeaveState.CLOSED,
    LeaveState.REJECTED,
    LeaveState.CANCELLED,
    LeaveState.WITHDRAWN,
}


class LeaveEvent:
    SUBMIT = "submit"
    SUBSTITUTE_ACCEPT = "substitute_accept"
    SUBSTITUTE_DECLINE = "substitute_decline"
    RENOMINATE = "renominate"
    WITHDRAW = "withdraw"

    UH_APPROVE = "uh_approve"
    UH_REJECT = "uh_reject"
    UH_RECOMMEND = "uh_recommend"
    UH_NOT_RECOMMEND = "uh_not_recommend"

    ROUTE = "route"
    SANCTION_APPROVE = "sanction_approve"
    SANCTION_REJECT = "sanction_reject"
    DIRECTOR_SELF_SANCTION = "director_self_sanction"

    REQUEST_CANCEL = "request_cancel"
    CANCEL_UH_APPROVE = "cancel_uh_approve"
    CANCEL_UH_REJECT = "cancel_uh_reject"
    CANCEL_UH_RECOMMEND = "cancel_uh_recommend"
    CANCEL_UH_NOT_RECOMMEND = "cancel_uh_not_recommend"
    CANCEL_ROUTE = "cancel_route"
    CANCEL_SANCTION_APPROVE = "cancel_sanction_approve"
    CANCEL_SANCTION_REJECT = "cancel_sanction_reject"

    REQUEST_EXTEND = "request_extend"
    EXT_SUBSTITUTE_ACCEPT = "ext_substitute_accept"
    EXT_SUBSTITUTE_DECLINE = "ext_substitute_decline"
    EXT_RENOMINATE = "ext_renominate"
    EXT_WITHDRAW = "ext_withdraw"
    EXT_UH_RECOMMEND = "ext_uh_recommend"
    EXT_UH_NOT_RECOMMEND = "ext_uh_not_recommend"
    EXT_ROUTE = "ext_route"
    EXT_SANCTION_APPROVE = "ext_sanction_approve"
    EXT_SANCTION_REJECT = "ext_sanction_reject"

    SUBMIT_RESUMPTION = "submit_resumption"
    VERIFY_RESUMPTION = "verify_resumption"


TRANSITIONS: dict[tuple[str, str], str] = {
    # Application flow
    (LeaveState.DRAFT, LeaveEvent.SUBMIT): LeaveState.PENDING_REVIEW,
    (
        LeaveState.SUBMITTED_PENDING_SUBSTITUTE,
        LeaveEvent.SUBSTITUTE_ACCEPT,
    ): LeaveState.PENDING_REVIEW,
    (
        LeaveState.SUBMITTED_PENDING_SUBSTITUTE,
        LeaveEvent.SUBSTITUTE_DECLINE,
    ): LeaveState.SUBSTITUTE_DECLINED,
    (
        LeaveState.SUBSTITUTE_DECLINED,
        LeaveEvent.RENOMINATE,
    ): LeaveState.SUBMITTED_PENDING_SUBSTITUTE,
    (LeaveState.SUBSTITUTE_DECLINED, LeaveEvent.WITHDRAW): LeaveState.WITHDRAWN,
    # Review (Unit Head)
    (LeaveState.PENDING_REVIEW, LeaveEvent.UH_APPROVE): LeaveState.APPROVED,
    (LeaveState.PENDING_REVIEW, LeaveEvent.UH_REJECT): LeaveState.REJECTED,
    (LeaveState.PENDING_REVIEW, LeaveEvent.UH_RECOMMEND): LeaveState.PENDING_ROUTING,
    (LeaveState.PENDING_REVIEW, LeaveEvent.UH_NOT_RECOMMEND): LeaveState.PENDING_ROUTING,
    # Routing (Establishment)
    (LeaveState.PENDING_ROUTING, LeaveEvent.ROUTE): LeaveState.PENDING_SANCTION,
    # Final Sanction
    (LeaveState.PENDING_SANCTION, LeaveEvent.SANCTION_APPROVE): LeaveState.APPROVED,
    (LeaveState.PENDING_SANCTION, LeaveEvent.SANCTION_REJECT): LeaveState.REJECTED,
    (LeaveState.PENDING_REVIEW, LeaveEvent.DIRECTOR_SELF_SANCTION): LeaveState.APPROVED,
    # Withdrawals (BR-EL-022)
    (LeaveState.SUBMITTED_PENDING_SUBSTITUTE, LeaveEvent.WITHDRAW): LeaveState.WITHDRAWN,
    (LeaveState.PENDING_REVIEW, LeaveEvent.WITHDRAW): LeaveState.WITHDRAWN,
    (LeaveState.PENDING_ROUTING, LeaveEvent.WITHDRAW): LeaveState.WITHDRAWN,
    (LeaveState.PENDING_SANCTION, LeaveEvent.WITHDRAW): LeaveState.WITHDRAWN,
    # Cancellation flow (BR-EL-023)
    (LeaveState.APPROVED, LeaveEvent.REQUEST_CANCEL): LeaveState.CANCELLATION_PENDING_REVIEW,
    (LeaveState.CANCELLATION_PENDING_REVIEW, LeaveEvent.CANCEL_UH_APPROVE): LeaveState.CANCELLED,
    (LeaveState.CANCELLATION_PENDING_REVIEW, LeaveEvent.CANCEL_UH_REJECT): LeaveState.APPROVED,
    (
        LeaveState.CANCELLATION_PENDING_REVIEW,
        LeaveEvent.CANCEL_UH_RECOMMEND,
    ): LeaveState.CANCELLATION_PENDING_ROUTING,
    (
        LeaveState.CANCELLATION_PENDING_REVIEW,
        LeaveEvent.CANCEL_UH_NOT_RECOMMEND,
    ): LeaveState.CANCELLATION_PENDING_ROUTING,
    (
        LeaveState.CANCELLATION_PENDING_ROUTING,
        LeaveEvent.CANCEL_ROUTE,
    ): LeaveState.CANCELLATION_PENDING_SANCTION,
    (
        LeaveState.CANCELLATION_PENDING_SANCTION,
        LeaveEvent.CANCEL_SANCTION_APPROVE,
    ): LeaveState.CANCELLED,
    (
        LeaveState.CANCELLATION_PENDING_SANCTION,
        LeaveEvent.CANCEL_SANCTION_REJECT,
    ): LeaveState.APPROVED,
    # Extension flow (BR-EL-025)
    (LeaveState.APPROVED, LeaveEvent.REQUEST_EXTEND): LeaveState.EXTENSION_PENDING_REVIEW,
    (
        LeaveState.EXTENSION_PENDING_SUBSTITUTE,
        LeaveEvent.EXT_SUBSTITUTE_ACCEPT,
    ): LeaveState.EXTENSION_PENDING_REVIEW,
    (
        LeaveState.EXTENSION_PENDING_SUBSTITUTE,
        LeaveEvent.EXT_SUBSTITUTE_DECLINE,
    ): LeaveState.EXTENSION_SUBSTITUTE_DECLINED,
    (
        LeaveState.EXTENSION_SUBSTITUTE_DECLINED,
        LeaveEvent.EXT_RENOMINATE,
    ): LeaveState.EXTENSION_PENDING_SUBSTITUTE,
    (LeaveState.EXTENSION_SUBSTITUTE_DECLINED, LeaveEvent.EXT_WITHDRAW): LeaveState.APPROVED,
    (
        LeaveState.EXTENSION_PENDING_REVIEW,
        LeaveEvent.EXT_UH_RECOMMEND,
    ): LeaveState.EXTENSION_PENDING_ROUTING,
    (
        LeaveState.EXTENSION_PENDING_REVIEW,
        LeaveEvent.EXT_UH_NOT_RECOMMEND,
    ): LeaveState.EXTENSION_PENDING_ROUTING,
    (
        LeaveState.EXTENSION_PENDING_ROUTING,
        LeaveEvent.EXT_ROUTE,
    ): LeaveState.EXTENSION_PENDING_SANCTION,
    (LeaveState.EXTENSION_PENDING_SANCTION, LeaveEvent.EXT_SANCTION_APPROVE): LeaveState.APPROVED,
    (LeaveState.EXTENSION_PENDING_SANCTION, LeaveEvent.EXT_SANCTION_REJECT): LeaveState.APPROVED,
    # Resumption flow (BR-EL-027, BR-EL-028)
    (LeaveState.APPROVED, LeaveEvent.SUBMIT_RESUMPTION): LeaveState.RESUMPTION_PENDING,
    (LeaveState.RESUMPTION_PENDING, LeaveEvent.VERIFY_RESUMPTION): LeaveState.CLOSED,
}


def transition(current_state: str, event: str) -> str:
    """Enforces valid state machine movement."""
    target = TRANSITIONS.get((current_state, event))
    if not target:
        raise InvalidLeaveTransitionError(
            f"Cannot perform event '{event}' on leave request in state '{current_state}'."
        )
    return target
