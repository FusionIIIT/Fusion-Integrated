"""Domain exceptions for Gymkhana."""


class DomainError(Exception):
    """Base domain exception."""


class DomainValidationError(DomainError):
    """Validation failure in domain logic."""


class DomainStateError(DomainError):
    """Illegal state transition in domain logic."""


class DomainAuthorizationError(DomainError):
    """Domain-level authorization violation."""
