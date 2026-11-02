"""Domain error types for Complaint Management System.

No Django or DRF imports.
"""


class ComplaintDomainError(Exception):
    """Base domain exception for CMS."""


class InvalidComplaintTransition(ComplaintDomainError):
    """Raised when an illegal lifecycle transition is attempted."""

    def __init__(self, from_status: str, to_status: str, reason: str = ""):
        msg = f"Cannot transition complaint from '{from_status}' to '{to_status}'."
        if reason:
            msg = f"{msg} Reason: {reason}"
        super().__init__(msg)
        self.from_status = from_status
        self.to_status = to_status


class ComplaintValidationError(ComplaintDomainError):
    """Raised when a business invariant or validation fails."""


class ComplaintPermissionDenied(ComplaintDomainError):
    """Raised when an actor lacks the required permission or role."""


class ComplaintAlreadyEscalated(ComplaintDomainError):
    """Raised when an already escalated complaint is escalated again."""


class ComplaintNotClosed(ComplaintDomainError):
    """Raised when an operation requires a Closed status but complaint is not closed."""


class ComplaintNotResolved(ComplaintDomainError):
    """Raised when an operation requires a Resolved status but complaint is not resolved."""


class ActiveRoleConstraintError(ComplaintDomainError):
    """Raised when CMS role constraint (exactly one active role-holder) is violated."""
