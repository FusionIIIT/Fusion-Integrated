"""Domain logic for Department module."""

from modules.dept.domain.exceptions import (
    AvailabilityError,
    ConflictError,
    DomainError,
    InvalidTransitionError,
    ValidationError,
)

__all__ = [
    "AvailabilityError",
    "ConflictError",
    "DomainError",
    "InvalidTransitionError",
    "ValidationError",
]
