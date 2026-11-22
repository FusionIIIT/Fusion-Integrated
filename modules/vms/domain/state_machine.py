from __future__ import annotations

from dataclasses import dataclass

NOT_SUBMITTED = "not_submitted"
PENDING = "pending"
PENDING_ADMIN = "pending_admin_contingency"
PENDING_URGENT = "pending_urgent_review"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
CANCELLED = "cancelled"
ON_SITE = "on_site"
COMPLETED = "completed"
TERMINATED = "terminated"

REQUEST_STATES = frozenset(
    {PENDING, PENDING_ADMIN, PENDING_URGENT, APPROVED, REJECTED, EXPIRED, CANCELLED}
)
TERMINAL_REQUEST_STATES = frozenset({REJECTED, EXPIRED, CANCELLED})


class InvalidTransition(ValueError):
    def __init__(self, source: str, event: str):
        super().__init__(f"A visit in {source!r} cannot process {event!r}.")
        self.source = source
        self.event = event


@dataclass(frozen=True)
class Transition:
    source: str
    event: str
    target: str
    actors: frozenset[str]
    required_permission: str


TRANSITIONS = (
    Transition(
        NOT_SUBMITTED, "submit", PENDING, frozenset({"visitor"}), "vms.visit_request.create"
    ),
    Transition(
        NOT_SUBMITTED, "submit_walk_in", PENDING, frozenset({"security"}), "vms.gate.validate"
    ),
    Transition(PENDING, "approve", APPROVED, frozenset({"host"}), "vms.visit_request.approve"),
    Transition(PENDING, "reject", REJECTED, frozenset({"host"}), "vms.visit_request.approve"),
    Transition(PENDING, "expire", EXPIRED, frozenset({"system"}), "vms.visit_request.expire"),
    Transition(
        PENDING, "require_admin", PENDING_ADMIN, frozenset({"system"}), "vms.visit_request.create"
    ),
    Transition(
        PENDING, "urgent_review", PENDING_URGENT, frozenset({"system"}), "vms.visit_request.create"
    ),
    Transition(
        PENDING_ADMIN,
        "approve_contingency",
        APPROVED,
        frozenset({"admin"}),
        "vms.visit_request.approve",
    ),
    Transition(
        PENDING_ADMIN,
        "reject_contingency",
        REJECTED,
        frozenset({"admin"}),
        "vms.visit_request.approve",
    ),
    Transition(
        PENDING_ADMIN,
        "expire_contingency",
        EXPIRED,
        frozenset({"system"}),
        "vms.visit_request.expire",
    ),
    Transition(
        PENDING_URGENT, "approve_urgent", PENDING, frozenset({"admin"}), "vms.visit_request.approve"
    ),
    Transition(
        PENDING_URGENT, "reject_urgent", REJECTED, frozenset({"admin"}), "vms.visit_request.approve"
    ),
    Transition(
        PENDING_URGENT, "expire_urgent", EXPIRED, frozenset({"system"}), "vms.visit_request.expire"
    ),
    Transition(APPROVED, "check_in", ON_SITE, frozenset({"security"}), "vms.gate.validate"),
    Transition(
        APPROVED, "terminate", TERMINATED, frozenset({"host", "admin"}), "vms.visit_request.update"
    ),
    Transition(
        ON_SITE,
        "check_out",
        COMPLETED,
        frozenset({"security", "visitor", "system"}),
        "vms.visit_log.create",
    ),
    Transition(
        ON_SITE, "terminate", TERMINATED, frozenset({"host", "admin"}), "vms.visit_request.update"
    ),
    Transition(
        TERMINATED, "record_exit", COMPLETED, frozenset({"security"}), "vms.visit_log.create"
    ),
)

_TRANSITION_INDEX = {(item.source, item.event): item for item in TRANSITIONS}


def resolve(source: str, event: str, actor: str | None = None) -> Transition:
    transition = _TRANSITION_INDEX.get((source, event))
    if transition is None or (actor is not None and actor not in transition.actors):
        raise InvalidTransition(source, event)
    return transition


def allowed_events(source: str, actor: str | None = None) -> tuple[str, ...]:
    return tuple(
        sorted(
            item.event
            for item in TRANSITIONS
            if item.source == source and (actor is None or actor in item.actors)
        )
    )
