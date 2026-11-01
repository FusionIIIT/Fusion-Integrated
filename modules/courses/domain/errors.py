"""Domain-level exceptions (pure Python)."""


class CourseDomainError(Exception):
    """Base domain exception for courses module."""


class UnauthorizedCourseActionError(CourseDomainError):
    """Raised when an actor attempts an action outside their role."""


class InvalidCourseDataError(CourseDomainError):
    """Raised when course workspace data fails domain invariants."""
