"""Domain exceptions for leave management (pure Python, framework-independent)."""
from __future__ import annotations


class LeaveDomainError(Exception):
    """Base exception for leave domain errors."""


class InvalidLeaveCalculation(LeaveDomainError):
    """Raised when leave day counting or dates are invalid."""


class InvalidStateTransition(LeaveDomainError):
    """Raised when an application state transition is not permitted."""
