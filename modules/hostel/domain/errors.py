class HostelDomainError(Exception):
    """Base error for hostel domain rule violations."""


class InvalidTransitionError(HostelDomainError):
    """Raised when an illegal state transition is attempted."""


class CapacityExceededError(HostelDomainError):
    """Raised when an operation would exceed room or hostel capacity (BR-HM-010)."""


class PermissionDeniedError(HostelDomainError):
    """Raised when actor role does not possess authority for action."""


class ScopeViolationError(HostelDomainError):
    """Raised when actor attempts to access data outside assigned scope (BR-HM-001..005, 035)."""


class DuplicateAllotmentError(HostelDomainError):
    """Raised when a student already holds an active allotment."""


class ValidationError(HostelDomainError):
    """Raised when mandatory business fields are missing or invalid."""
