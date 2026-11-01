"""RSPC domain exceptions.
Pure Python — no Django or DRF imports.
"""


class RspcDomainError(Exception):
    """Base exception for all RSPC domain validation and state-transition errors."""

    def __init__(self, message: str, code: str = "rspc_domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidTransitionError(RspcDomainError):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, from_state: str, to_state: str, entity_name: str = "record"):
        super().__init__(
            f"Cannot move {entity_name} from {from_state!r} to {to_state!r}.",
            code="invalid_transition",
        )
        self.from_state = from_state
        self.to_state = to_state
        self.entity_name = entity_name


class PermissionDeniedDomainError(RspcDomainError):
    """Raised when an actor lacks the role or permission for a transition or action."""

    def __init__(self, actor_role: str, action: str):
        super().__init__(
            f"Role {actor_role!r} is not authorized to perform {action!r}.",
            code="permission_denied",
        )
        self.actor_role = actor_role
        self.action = action


class GuardFailedError(RspcDomainError):
    """Raised when a business rule guard condition fails."""

    def __init__(self, guard_name: str, message: str):
        super().__init__(message, code=f"guard_{guard_name}")
        self.guard_name = guard_name


class MandatoryFieldMissingError(RspcDomainError):
    """BR-RSPC-013: Mandatory fields must be present."""

    def __init__(self, missing_fields: list[str]):
        super().__init__(
            f"Mandatory fields missing: {', '.join(missing_fields)}.",
            code="mandatory_fields_missing",
        )
        self.missing_fields = missing_fields


class BudgetExceededError(RspcDomainError):
    """BR-RSPC-035: Procurement/financial request must match sanctioned budget."""

    def __init__(self, requested: float, available: float):
        super().__init__(
            f"Requested amount ({requested}) exceeds available sanctioned budget ({available}).",
            code="budget_exceeded",
        )
        self.requested = requested
        self.available = available


class DelegatedLimitExceededError(RspcDomainError):
    """BR-RSPC-032, BR-RSPC-068: Approval exceeds delegated limit and requires escalation."""

    def __init__(self, amount: float, limit: float, authority: str = "Dean-RSPC"):
        super().__init__(
            f"Amount ({amount}) exceeds {authority} limit ({limit}) and requires escalation.",
            code="delegated_limit_exceeded",
        )
        self.amount = amount
        self.limit = limit
        self.authority = authority


class LifecycleNotPermittedError(RspcDomainError):
    """BR-RSPC-065: Updates are not permitted in the current project lifecycle state."""

    def __init__(self, current_state: str, action: str = "update"):
        super().__init__(
            f"Cannot {action} project in lifecycle state {current_state!r}.",
            code="lifecycle_not_permitted",
        )
        self.current_state = current_state
