from __future__ import annotations

from dataclasses import dataclass, field

SUBSTITUTE_PENDING = "substitute_pending"
UNIT_REVIEW = "unit_review"
ROUTING = "routing"
SANCTION = "sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"

# Actor kinds named by the transition table.
STAFF = "staff"
RECRUITER = "recruiter"
STUDENT = "student"
DEPUTY_REGISTRAR = "deputy_registrar"
REGISTRAR = "registrar"
DIRECTOR = "director"

TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED})


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        SUBSTITUTE_PENDING, UNIT_REVIEW, "leave.request.review", frozenset({STAFF, RECRUITER})
    ),
    Transition(SUBSTITUTE_PENDING, WITHDRAWN, "leave.request.cancel", frozenset({STUDENT})),
    Transition(SUBSTITUTE_PENDING, REJECTED, "leave.request.reject", frozenset({STUDENT})),
    Transition(UNIT_REVIEW, APPROVED, "leave.request.approve", frozenset({STAFF, RECRUITER})),
    Transition(UNIT_REVIEW, REJECTED, "leave.request.reject", frozenset({STAFF, RECRUITER})),
    Transition(UNIT_REVIEW, ROUTING, "leave.request.route", frozenset({DEPUTY_REGISTRAR})),
    Transition(UNIT_REVIEW, WITHDRAWN, "leave.request.cancel", frozenset({STUDENT})),
    Transition(ROUTING, SANCTION, "leave.request.sanction", frozenset({REGISTRAR, DIRECTOR})),
    Transition(ROUTING, WITHDRAWN, "leave.request.cancel", frozenset({STUDENT})),
    Transition(SANCTION, APPROVED, "leave.request.approve", frozenset({STAFF, RECRUITER})),
    Transition(SANCTION, REJECTED, "leave.request.reject", frozenset({STAFF, RECRUITER})),
    Transition(SANCTION, WITHDRAWN, "leave.request.cancel", frozenset({STUDENT})),
    Transition(APPROVED, CANCELLED, "leave.request.cancel", frozenset({STUDENT})),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    """The single lookup every write goes through. `actor_kind` is optional
    only so the table can be introspected; every service call supplies it."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted(
        t.to for t in TRANSITIONS if t.frm == frm and (actor_kind is None or actor_kind in t.actors)
    )


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move a leave request from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(f"{actor_kind} may not move a request from {frm} to {to}.")


def can_transition(current: str, target: str) -> bool:
    """Return True if the transition from current to target is allowed."""
    return (current, target) in _INDEX


def assert_transition(current: str, target: str) -> None:
    """Raise InvalidTransition if the transition from current to target is not allowed."""
    if not can_transition(current, target):
        raise InvalidTransition(current, target)
