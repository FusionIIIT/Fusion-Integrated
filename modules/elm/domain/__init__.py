"""ELM Domain layer. Pure Python, no Django/DRF dependencies."""
from .state_machine import (
    APPROVED,
    PENDING,
    REJECTED,
    TERMINAL_STATES,
    TRANSITIONS,
    InvalidTransitionError,
    calculate_leave_days,
    validate_transition,
)

__all__ = [
    "APPROVED",
    "PENDING",
    "REJECTED",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "InvalidTransitionError",
    "calculate_leave_days",
    "validate_transition",
]
