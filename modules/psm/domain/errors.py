# Pure-Python domain exceptions translated to HTTP errors in services/.
from __future__ import annotations


class PsmRuleError(Exception):
    """Base domain rule violation carrying a stable machine code."""

    def __init__(self, message: str, *, code: str, details: list | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or []


class InvalidTransitionError(PsmRuleError):
    """Raised when an entity cannot move between two lifecycle states."""

    def __init__(self, entity: str, frm: str, to: str):
        super().__init__(
            f"Cannot move {entity} from '{frm}' to '{to}'; check its current status.",
            code="invalid_transition",
        )
        self.entity, self.frm, self.to = entity, frm, to


class ActorNotAllowedError(PsmRuleError):
    """Raised when an actor lane is not permitted for a state transition."""

    def __init__(self, actor_lane: str, entity: str, frm: str, to: str):
        super().__init__(
            f"Role '{actor_lane}' cannot move {entity} from '{frm}' to '{to}'.",
            code="actor_not_allowed",
        )
        self.actor_lane, self.entity, self.frm, self.to = actor_lane, entity, frm, to


class ValidationRuleError(PsmRuleError):
    """Raised when required fields or domain invariants fail validation."""


class ConflictRuleError(PsmRuleError):
    """Raised when a state, policy, or concurrency gate refuses an action."""
