"""Pure Python domain errors for ELM.
"""
from __future__ import annotations


class ElmDomainError(Exception):
    """Base domain exception for Employee Leave Management."""


class InvalidLeaveTransitionError(ElmDomainError):
    """Raised when an invalid state transition is attempted."""


class InsufficientBalanceError(ElmDomainError):
    """Raised when leave quota is insufficient for the requested days."""


class LeaveValidationError(ElmDomainError):
    """Raised when application inputs fail domain business validation rules."""

# Export public symbols for convenient imports
__all__ = [
    "ElmDomainError",
    "InvalidLeaveTransitionError",
    "InsufficientBalanceError",
    "LeaveValidationError",
]
