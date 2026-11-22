"""VMS Visit State Machine.
Pure Python state-machine transitions and invariant validations.
"""

from __future__ import annotations

from enum import StrEnum


class VisitState(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    ON_SITE = "on_site"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TransitionTrigger(StrEnum):
    HOST_APPROVE = "host_approve"
    HOST_REJECT = "host_reject"
    VISITOR_CANCEL = "visitor_cancel"
    ADMIN_CANCEL = "admin_cancel"
    GATE_CHECK_IN = "gate_check_in"
    GATE_CHECK_OUT = "gate_check_out"
    AUTO_CHECKOUT = "auto_checkout"
    TIMEOUT = "timeout"


TERMINAL_STATES = frozenset(
    {
        VisitState.REJECTED.value,
        VisitState.COMPLETED.value,
        VisitState.CANCELLED.value,
        VisitState.EXPIRED.value,
    }
)

# Allowed state transitions: (source_state, trigger) -> target_state
ALLOWED_TRANSITIONS: dict[tuple[str, str], str] = {
    (VisitState.REQUESTED.value, TransitionTrigger.HOST_APPROVE.value): VisitState.APPROVED.value,
    (VisitState.REQUESTED.value, TransitionTrigger.HOST_REJECT.value): VisitState.REJECTED.value,
    (
        VisitState.REQUESTED.value,
        TransitionTrigger.VISITOR_CANCEL.value,
    ): VisitState.CANCELLED.value,
    (VisitState.REQUESTED.value, TransitionTrigger.ADMIN_CANCEL.value): VisitState.CANCELLED.value,
    (VisitState.REQUESTED.value, TransitionTrigger.TIMEOUT.value): VisitState.EXPIRED.value,
    (VisitState.APPROVED.value, TransitionTrigger.GATE_CHECK_IN.value): VisitState.ON_SITE.value,
    (VisitState.APPROVED.value, TransitionTrigger.ADMIN_CANCEL.value): VisitState.CANCELLED.value,
    (VisitState.APPROVED.value, TransitionTrigger.TIMEOUT.value): VisitState.EXPIRED.value,
    (VisitState.ON_SITE.value, TransitionTrigger.GATE_CHECK_OUT.value): VisitState.COMPLETED.value,
    (VisitState.ON_SITE.value, TransitionTrigger.AUTO_CHECKOUT.value): VisitState.COMPLETED.value,
}


class InvalidStateTransitionError(Exception):
    def __init__(
        self, current_state: str, trigger: str, target_state: str | None = None, message: str = ""
    ):
        self.current_state = current_state
        self.trigger = trigger
        self.target_state = target_state
        msg = message or f"Cannot execute transition '{trigger}' from state '{current_state}'."
        super().__init__(msg)


def validate_transition(current_state: str, trigger: str) -> str:
    """Validate state transition and return resulting state or raise InvalidStateTransitionError."""
    if current_state in TERMINAL_STATES:
        msg = f"Visit in terminal state '{current_state}' cannot transition further (rule BR-023)."
        raise InvalidStateTransitionError(
            current_state,
            trigger,
            message=msg,
        )

    key = (current_state, trigger)
    if key not in ALLOWED_TRANSITIONS:
        raise InvalidStateTransitionError(
            current_state,
            trigger,
            message=f"Transition '{trigger}' is not permitted from state '{current_state}'.",
        )

    return ALLOWED_TRANSITIONS[key]
