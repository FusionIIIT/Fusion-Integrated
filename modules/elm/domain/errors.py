"""Domain-level exceptions for Employee Leave Management.

Pure Python. No Django, DRF or database imports.
"""
from __future__ import annotations


class ElmDomainError(Exception):
    """Base error for ELM domain violations."""

    def __init__(self, message: str, code: str = "domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidTransitionError(ElmDomainError):
    """Raised when an illegal status change is attempted."""

    def __init__(self, frm: str, to: str):
        super().__init__(
            f"Cannot move leave application from '{frm}' to '{to}'.",
            code="invalid_transition",
        )
        self.frm, self.to = frm, to


class InvalidDateRangeError(ElmDomainError):
    """Raised when end_date < start_date or date range is malformed."""

    def __init__(self, message: str = "Leave end date cannot be earlier than start date."):
        super().__init__(message, code="invalid_date_range")


class OverlappingLeaveError(ElmDomainError):
    """Raised when an applicant has an active leave application for the same period."""

    def __init__(
        self,
        message: str = "You already have an active leave application for these dates.",
    ):
        super().__init__(message, code="overlapping_leave")
