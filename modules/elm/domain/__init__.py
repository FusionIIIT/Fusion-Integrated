"""Pure Python domain layer for Employee Leave Management.

Zero external framework dependencies: no Django, no DRF, no Celery.
"""
from modules.elm.domain.entities import LeaveCategory, LeaveStatus, StateTransitionResult
from modules.elm.domain.errors import (
    ElmDomainError,
    InsufficientBalanceError,
    InvalidLeaveTransitionError,
    LeaveValidationError,
)

__all__ = [
    "LeaveCategory",
    "LeaveStatus",
    "StateTransitionResult",
    "ElmDomainError",
    "InsufficientBalanceError",
    "InvalidLeaveTransitionError",
    "LeaveValidationError",
]
