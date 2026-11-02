"""Domain package for Complaint Management System. Pure Python — no framework imports."""
from .errors import (
    ActiveRoleConstraintError,
    ComplaintAlreadyEscalated,
    ComplaintNotClosed,
    ComplaintNotResolved,
    ComplaintPermissionDenied,
    ComplaintValidationError,
    InvalidComplaintTransition,
)
from .state_machine import (
    ClosureVerification,
    ComplaintPriority,
    ComplaintStatus,
    EscalationType,
    ReopeningStatus,
    TERMINAL_STATES,
    TRANSITIONS,
    Transition,
    validate_transition,
)

__all__ = [
    "ActiveRoleConstraintError",
    "ClosureVerification",
    "ComplaintAlreadyEscalated",
    "ComplaintNotClosed",
    "ComplaintNotResolved",
    "ComplaintPermissionDenied",
    "ComplaintPriority",
    "ComplaintStatus",
    "ComplaintValidationError",
    "EscalationType",
    "InvalidComplaintTransition",
    "ReopeningStatus",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "Transition",
    "validate_transition",
]
