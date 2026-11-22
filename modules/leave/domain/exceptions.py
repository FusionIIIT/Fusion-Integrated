"""Domain-specific exceptions for Leave Management (Pure Python)."""

from __future__ import annotations


class LeaveDomainError(Exception):
    """Base exception for all leave domain rule violations."""

    def __init__(self, message: str, code: str = "leave_domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidStateTransitionError(LeaveDomainError):
    """Raised when an illegal workflow state transition is attempted."""

    def __init__(self, current_state: str, next_state: str):
        super().__init__(
            f"Cannot transition leave application from {current_state!r} to {next_state!r}.",
            code="invalid_state_transition",
        )
        self.current_state = current_state
        self.next_state = next_state


class LeaveCalculationError(LeaveDomainError):
    """Raised when leave day calculation or holiday constraints fail."""

    def __init__(self, message: str, code: str = "invalid_dates"):
        super().__init__(message, code=code)
