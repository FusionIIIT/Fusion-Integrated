
"""Pure state-transition rules for Employee Leave Management."""

from dataclasses import dataclass

DRAFT = "draft"
SUBMITTED = "submitted"
PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"


class InvalidTransition(ValueError):
    """Raised when a leave request cannot make the requested transition."""


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    action: str


TRANSITIONS = (
    Transition(DRAFT, SUBMITTED, "submit"),
    Transition(SUBMITTED, PENDING, "begin_approval"),
    Transition(PENDING, APPROVED, "approve"),
    Transition(PENDING, REJECTED, "reject"),
    Transition(DRAFT, WITHDRAWN, "withdraw"),
    Transition(SUBMITTED, WITHDRAWN, "withdraw"),
    Transition(APPROVED, CANCELLED, "cancel"),
)


def resolve(source: str, action: str) -> Transition:
    """Resolve a permitted action or raise InvalidTransition."""
    for transition in TRANSITIONS:
        if transition.source == source and transition.action == action:
            return transition

    raise InvalidTransition(
        f"Action '{action}' is not allowed from status '{source}'."
    )


def allowed_actions(source: str) -> tuple[str, ...]:
    """List the permitted actions for a request's current status."""
    return tuple(
        transition.action
        for transition in TRANSITIONS
        if transition.source == source
    )
