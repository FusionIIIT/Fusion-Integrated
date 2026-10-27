"""Leave request state machine.

Pure Python domain logic following BR-EL-022 through BR-EL-035.
No Django/DRF imports here.
"""
from __future__ import annotations

from datetime import date
from enum import Enum


class LeaveRequestState(Enum):
    """Leave request states."""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    RESUMED = "resumed"


class LeaveRequestStateMachine:
    """State machine for leave requests following BR-EL-022 through BR-EL-035."""

    # Valid transitions
    TRANSITIONS = {
        # Initial state
        LeaveRequestState.DRAFT: {
            "submit": LeaveRequestState.PENDING,
            "cancel": LeaveRequestState.CANCELLED,
        },
        # Pending state
        LeaveRequestState.PENDING: {
            "approve": LeaveRequestState.APPROVED,
            "reject": LeaveRequestState.CANCELLED,
            "withdraw": LeaveRequestState.DRAFT,
        },
        # Approved state
        LeaveRequestState.APPROVED: {
            "cancel": LeaveRequestState.CANCELLED,
            "resumefromresigned": LeaveRequestState.RESUMED,
        },
        # Cancelled state - final state
        LeaveRequestState.CANCELLED: {},
        # Resumed state - final state
        LeaveRequestState.RESUMED: {},
    }

    # BR-EL-022: Immediate withdrawal of pending request
    WITHDRAWAL_ALLOWED = True

    # BR-EL-023: Cancellation of approved leave before start
    CANCELLATION_BEFORE_START = True

    # BR-EL-024: Fresh application after cancellation
    FRESH_APPLICATION_ALLOWED = True

    # BR-EL-025: Extension of ongoing EL/COL/VL
    EXTENSION_ALLOWED = True

    # BR-EL-027: Resumption applicability and review authority
    RESUMPTION_REQUIRES_REVIEW = True

    # BR-EL-028: Normal, early, and late resumption outcome
    RESUMPTION_OUTCOMES = ["Normal", "Early", "Late"]

    def __init__(self, request_state: LeaveRequestState):
        """Initialize state machine with current state."""
        self.current_state = request_state
        self.transitions = self.TRANSITIONS.get(request_state, {})
        self.history: list[str] = []

    def can_transition(self, action: str) -> tuple[bool, str]:
        """Check if transition is valid."""
        if self.current_state not in self.transitions:
            return False, f"Unknown state: {self.current_state}"

        if action not in self.transitions[self.current_state]:
            return False, f"Invalid transition from {self.current_state}: {action}"

        return True, None

    def transition(self, action: str) -> LeaveRequestState:
        """Execute transition."""
        if not self.can_transition(action):
            raise ValueError(f"Cannot transition from {self.current_state} with {action}")

        new_state = self.transitions[self.current_state][action]
        self.current_state = new_state
        self.history.append(f"{self.current_state.value} -> {new_state.value}")
        return new_state

    def get_current_state(self) -> LeaveRequestState:
        """Get current state."""
        return self.current_state

    def get_state_label(self) -> str:
        """Get human-readable state label."""
        return self.current_state.value

    def get_history(self) -> list[str]:
        """Get transition history."""
        return self.history

    def is_final_state(self) -> bool:
        """Check if current state is final."""
        return self.current_state in (LeaveRequestState.CANCELLED, LeaveRequestState.RESUMED)

    def get_next_allowed_actions(self) -> list[str]:
        """Get list of allowed actions from current state."""
        if self.current_state not in self.transitions:
            return []
        return list(self.transitions[self.current_state].keys())

    def validate_action(self, action: str, request: dict, current_date: date) -> tuple[bool, str]:
        """Validate action based on business rules."""
        # BR-EL-023: Cancellation of approved leave before start
        if action == "cancel" and request.get("status") == "approved":
            start_date = request.get("start_date")
            if start_date and start_date < current_date:
                return False, "Cannot cancel approved leave that has already started"

        # BR-EL-025: Extension of ongoing EL/COL/VL
        if action == "extend" and request.get("status") in ("approved", "pending"):
            if request.get("category") not in ("EL", "COL", "VL"):
                return False, "Extension only allowed for EL, COL, or VL"

        # BR-EL-027: Resumption requires review
        if action == "resumefromresigned":
            if not request.get("resigned", False):
                return False, "Resumption requires resignation record"

        # BR-EL-028: Normal, early, late resumption outcomes
        if action == "resumefromresigned":
            start_date = request.get("start_date")
            current_date = date.today()
            if start_date and start_date > current_date:
                return False, "Resumption date cannot be in the future"

        return True, None


class LeaveSanctionState:
    """State machine for leave sanctioning."""

    SANCTION_STATES = [
        "submitted",
        "reviewing",
        "approved",
        "rejected",
        "pending_escalation",
    ]

    def __init__(self, state: str):
        self.state = state
        self.transitions = {
            "submitted": ["reviewing"],
            "reviewing": ["approved", "rejected", "pending_escalation"],
            "approved": [],
            "rejected": [],
            "pending_escalation": ["approved", "rejected"],
        }

    def can_transition(self, action: str) -> bool:
        return self.state in self.transitions.get(action, [])

    def transition(self, action: str):
        if not self.can_transition(action):
            raise ValueError(f"Cannot transition from {self.state} to {action}")
        self.state = action


def get_valid_transition(
    from_state: str, action: str
) -> tuple[bool, str]:
    """Get valid transition for a state machine."""
    state_machine = LeaveRequestStateMachine(LeaveRequestState(from_state))
    return state_machine.can_transition(action), None


def get_next_state(
    from_state: str, action: str
) -> tuple[bool, str]:
    """Get next state from a state machine."""
    state_machine = LeaveRequestStateMachine(LeaveRequestState(from_state))
    return True, state_machine.transitions[from_state][action]


def get_request_state_label(state: str) -> str:
    """Get human-readable state label."""
    return LeaveRequestState(state).value if state in [s.value for s in LeaveRequestState] else state


def get_request_state_value(label: str) -> str:
    """Get state value from label."""
    return LeaveRequestState(label).value if label in [s.value for s in LeaveRequestState] else label
