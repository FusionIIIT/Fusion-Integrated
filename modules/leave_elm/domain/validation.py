"""Validation helpers for leave substitute workflow transitions."""

from .states import LeaveWorkflowState as State
from .transitions import TRANSITIONS


def is_valid_transition(current_state: State, target_state: State) -> bool:
    """Whether the requested state change is part of the workflow."""
    return any(
        transition.source == current_state and transition.target == target_state
        for transition in TRANSITIONS
    )


def validate_transition(current_state: State, target_state: State) -> None:
    """Raise ``ValueError`` unless the requested state change is legal."""
    if not is_valid_transition(current_state, target_state):
        raise ValueError(f"Illegal leave workflow transition: {current_state} -> {target_state}")
