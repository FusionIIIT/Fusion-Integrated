"""Domain exceptions for Leave Management (ELM).

Pure Python — no Django or HTTP dependencies.
"""


class ElmDomainError(Exception):
    """Base error for all ELM domain violations."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidLeaveDateError(ElmDomainError):
    """Raised when dates are illogical, past, or invalid."""


class InsufficientLeaveBalanceError(ElmDomainError):
    """Raised when the employee has insufficient leave balance."""


class OverlappingLeaveError(ElmDomainError):
    """Raised when a requested leave overlaps with active pending/approved leave."""


class IneligibleCategoryError(ElmDomainError):
    """Raised when an employee is ineligible for a leave category (e.g. non-faculty VL)."""


class InvalidSubstituteError(ElmDomainError):
    """Raised when substitute nomination violates policy."""


class IllegalStateTransitionError(ElmDomainError):
    """Raised when an invalid action is attempted on a leave request."""


class StationLeaveValidationError(ElmDomainError):
    """Raised when required station leave details are missing or invalid."""
