"""Club and membership lifecycles (BW-GYM-01, BW-GYM-03) as one declarative table."""
from __future__ import annotations

from dataclasses import dataclass

CLUB = "club"
MEMBERSHIP = "membership"

# "No record yet": the source state of a creating transition.
NONE = "none"
OPEN = "open"
CONFIRMED = "confirmed"
STATES = (OPEN, CONFIRMED)

CREATE = "create"
APPLY = "apply"
APPROVE = "approve"

STUDENT_ADMIN = "student_admin"
CLUB_HEAD = "club_head"
STUDENT = "student"


class InvalidTransition(Exception):
    def __init__(self, machine: str, frm: str, event: str):
        super().__init__(f"A {machine} in state {frm!r} cannot be sent {event!r}.")
        self.machine, self.frm, self.event = machine, frm, event


class ActorNotAllowed(Exception):
    def __init__(self, machine: str, frm: str, event: str, actor: str):
        super().__init__(f"A {actor} may not {event} a {machine} in state {frm!r}.")
        self.machine, self.frm, self.event, self.actor = machine, frm, event, actor


@dataclass(frozen=True)
class Transition:
    machine: str
    frm: str
    event: str
    actor: str
    to: str
    rules: tuple[str, ...]


TRANSITIONS: tuple[Transition, ...] = (
    Transition(CLUB, NONE, CREATE, STUDENT_ADMIN, OPEN,
               ("BR-GYM-001", "BR-GYM-002", "BR-GYM-003", "BR-GYM-004")),
    Transition(CLUB, OPEN, APPROVE, STUDENT_ADMIN, CONFIRMED, ("BR-GYM-004",)),
    Transition(MEMBERSHIP, NONE, APPLY, STUDENT, OPEN,
               ("BR-GYM-007", "BR-GYM-008", "BR-GYM-009")),
    Transition(MEMBERSHIP, OPEN, APPROVE, CLUB_HEAD, CONFIRMED,
               ("BR-GYM-010", "BR-GYM-011")),
)

_INDEX = {(t.machine, t.frm, t.event): t for t in TRANSITIONS}


def resolve(machine: str, frm: str, event: str, actor: str) -> Transition:
    """The one lookup every lifecycle write goes through."""
    t = _INDEX.get((machine, frm, event))
    if t is None:
        raise InvalidTransition(machine, frm, event)
    if t.actor != actor:
        raise ActorNotAllowed(machine, frm, event, actor)
    return t
