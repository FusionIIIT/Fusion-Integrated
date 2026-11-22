class OAPDomainError(Exception):
    """Base exception for all domain business rule and validation failures in OAP."""


class InvalidStateTransitionError(OAPDomainError):
    """Raised when an illegal lifecycle transition is attempted."""


class IneligibleRequestError(OAPDomainError):
    """Raised when a student does not meet policy criteria (CPI, backlogs, dues)."""


class UnauthorizedApprovalError(OAPDomainError):
    """Raised when a non-authorized actor attempts a workflow decision."""


class DuplicateActiveRequestError(OAPDomainError):
    """Raised when an active duplicate request is already pending."""
