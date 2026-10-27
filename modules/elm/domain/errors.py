"""Domain errors for Employee Leave Management (ELM).

Per the Fusion Module Authoring Guide, domain errors are pure Python exceptions
with no DRF dependencies.
"""


class ElmDomainError(Exception):
    """Base domain exception for ELM."""


class InvalidTransition(ElmDomainError):
    """Raised when an illegal workflow state transition is attempted."""


class InsufficientLeaveBalance(ElmDomainError):
    """Raised when an applicant requests more leave days than available balance."""


class OverlappingLeaveError(ElmDomainError):
    """Raised when requested dates conflict with another approved or pending leave (BR-EL-012)."""


class InvalidSubstituteError(ElmDomainError):
    """Raised when a nominated substitute fails eligibility checks (BR-EL-014)."""


class InvalidLeaveDatesError(ElmDomainError):
    """Raised when start/end dates are inverted, past, or invalid for the category."""


class PolicyValidationError(ElmDomainError):
    """Raised when leave policy constraints (e.g. vacation period, medical certificate) are violated."""
