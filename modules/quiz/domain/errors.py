"""Errors raised by pure Quiz Management domain functions."""


class DomainError(ValueError):
    """Base error with a stable code suitable for later service translation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class InvalidTransition(DomainError):
    """Raised when a lifecycle event has no declared transition."""

    def __init__(self, aggregate: str, current: str | None, event: str) -> None:
        super().__init__(
            "invalid_transition",
            f"Cannot apply {event!r} to {aggregate} state {current!r}.",
        )
        self.aggregate = aggregate
        self.current = current
        self.event = event


class ActorNotAllowed(DomainError):
    """Raised when a domain actor does not match a declared transition."""

    def __init__(self, actor: str, event: str) -> None:
        super().__init__(
            "actor_not_allowed",
            f"Actor {actor!r} may not perform {event!r}.",
        )
        self.actor = actor
        self.event = event


class GuardFailed(DomainError):
    """Raised when a required transition guard is absent or false."""

    def __init__(self, guard: str) -> None:
        super().__init__(
            "transition_guard_failed",
            f"The {guard.replace('_', ' ')} condition is not satisfied.",
        )
        self.guard = guard


class DefinitionValidationError(DomainError):
    """Raised with field-specific validation issue codes."""

    def __init__(self, issues: tuple[tuple[str, str], ...]) -> None:
        details = "; ".join(f"{field}: {message}" for field, message in issues)
        super().__init__("invalid_quiz_definition", details)
        self.issues = issues


class AttemptEligibilityError(DomainError):
    """Raised when the supplied facts do not permit a new attempt."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)


class UnresolvedPolicyError(DomainError):
    """Raised when requested behavior depends on an unresolved policy gate."""

    def __init__(self, policy_id: str, message: str) -> None:
        super().__init__("unresolved_policy", message)
        self.policy_id = policy_id
