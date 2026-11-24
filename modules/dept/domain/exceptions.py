"""Domain exceptions for Department module."""


class DomainError(Exception):
    """Base domain exception."""


class InvalidTransitionError(DomainError):
    """Raised when an illegal state transition is attempted."""


class ValidationError(DomainError):
    """Raised when domain constraints or invariants are violated."""


class AvailabilityError(DomainError):
    """Raised when stock inventory is insufficient."""


class ConflictError(DomainError):
    """Raised when timetable schedules conflict."""
