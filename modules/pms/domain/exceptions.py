"""Domain-level exceptions for PMS."""


class DomainRuleError(Exception):
    """Base exception for all PMS business rule violations."""

    def __init__(self, message: str, rule_id: str | None = None):
        super().__init__(message)
        self.message = message
        self.rule_id = rule_id


class ValidationError(DomainRuleError):
    """Raised when application fields or document validation fails."""


class InvalidTransitionError(DomainRuleError):
    """Raised when an illegal lifecycle state transition is attempted."""

    def __init__(self, current_status: str, target_status: str, message: str = ""):
        msg = message or f"Illegal transition from {current_status!r} to {target_status!r}."
        super().__init__(msg)
        self.current_status = current_status
        self.target_status = target_status


class ActorNotAllowedError(DomainRuleError):
    """Raised when an actor attempts an action outside their role or assigned scope."""

    def __init__(self, actor: str, action: str):
        super().__init__(f"Actor {actor!r} is not authorized to perform {action!r}.")
        self.actor = actor
        self.action = action


class ConflictOfInterestError(DomainRuleError):
    """Raised when reviewer or assigner has a conflict of interest (e.g. is inventor)."""


class DeadlineExpiredError(DomainRuleError):
    """Raised when a time-bound action (review, revision, appeal) has expired."""
