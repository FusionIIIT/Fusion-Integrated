"""Domain exceptions for Super Admin."""


class DomainValidationError(Exception):
    pass


class InvalidTransitionError(Exception):
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        super().__init__(f"Cannot move from {from_state!r} to {to_state!r}. {reason}".strip())
        self.from_state = from_state
        self.to_state = to_state


class ActorNotAllowedError(Exception):
    def __init__(self, actor: str, from_state: str, to_state: str):
        super().__init__(
            f"Actor {actor!r} is not authorized to transition from {from_state!r} to {to_state!r}."
        )
        self.actor = actor
        self.from_state = from_state
        self.to_state = to_state


class GuardFailedError(Exception):
    def __init__(self, guard_name: str, message: str = ""):
        super().__init__(message or f"Guard {guard_name!r} failed.")
        self.guard_name = guard_name


class PolicyConflictError(Exception):
    pass


class ImmutableRecordError(Exception):
    pass


# Aliases for domain policy and state machine compatibility
InvalidStateTransitionError = InvalidTransitionError
ValidationDomainError = DomainValidationError
PolicyViolationError = PolicyConflictError
SingularRoleConflictError = PolicyConflictError
DualAuthorizationRequiredError = PolicyConflictError
PurgeNotEligibleError = PolicyConflictError
ReversibilityExpiredError = PolicyConflictError
SuperAdminDomainError = DomainValidationError
