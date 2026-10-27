"""Domain-level exceptions for Employee Leave Management."""


class ELMError(Exception):
    """Base exception for all ELM domain errors."""
    pass


class ELMValidationError(ELMError):
    """Raised when leave input validation fails."""
    pass


class EligibilityError(ELMValidationError):
    """Raised when an employee is ineligible for a requested leave category."""
    pass


class BalanceExceededError(ELMValidationError):
    """Raised when available balance is insufficient for the requested leave."""
    pass


class OverlapError(ELMValidationError):
    """Raised when requested dates conflict with active pending or approved leave."""
    pass


class CalendarValidationError(ELMValidationError):
    """Raised when RH or VL dates violate published calendar rules."""
    pass


class SubstituteError(ELMValidationError):
    """Raised when a nominated substitute violates eligibility or availability rules."""
    pass


class InvalidStateTransitionError(ELMError):
    """Raised when a requested workflow transition is illegal from the current state."""
    pass


class UnauthorizedActionError(ELMError):
    """Raised when an actor lacks the required role or ownership for an action."""
    pass
