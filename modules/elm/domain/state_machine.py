"""The leave application state machine (blueprint §(c), BR-08..BR-10).

A declarative table, so an illegal move is refused by construction and "who may
do this, and under which permission?" has exactly one answer per edge.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"

#: A status an overlap check and the per-day unique index still consider live.
ACTIVE = frozenset({PENDING, APPROVED})
TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED})
ALL_STATUSES = frozenset({PENDING, APPROVED, REJECTED, WITHDRAWN, CANCELLED})

EMPLOYEE = "employee"
APPROVER = "approver"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move a leave application from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"A {actor_kind} may not move a leave application from {frm!r} to {to!r}.")
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


TRANSITIONS: tuple[Transition, ...] = (
    # An approver's decision; the service refuses a self-approval before this runs.
    Transition(PENDING, APPROVED, "elm.application.approve",
               frozenset({APPROVER}),
               ("not_self_approval", "balance_sufficient")),
    Transition(PENDING, REJECTED, "elm.application.approve",
               frozenset({APPROVER}),
               ("not_self_approval", "has_decision_note")),

    # The applicant's own moves.
    Transition(PENDING, WITHDRAWN, "elm.application.delete",
               frozenset({EMPLOYEE}), ()),
    Transition(APPROVED, CANCELLED, "elm.application.delete",
               frozenset({EMPLOYEE}), ("not_finished",)),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    """The single lookup every write goes through."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted(t.to for t in TRANSITIONS
                  if t.frm == frm
                  and (actor_kind is None or actor_kind in t.actors))
