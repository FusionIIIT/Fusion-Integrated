"""The quiz and attempt state machines (CW-QZ-01, CW-QZ-02, CW-QZ-03).

Declarative tables of legal moves, so an illegal transition is impossible to
express rather than merely rejected. Pure Python, so the rules test with no DB.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# -- quiz lifecycle: Draft → Scheduled → Available → Closed → Archived -------
DRAFT = "draft"
SCHEDULED = "scheduled"
AVAILABLE = "available"
CLOSED = "closed"
ARCHIVED = "archived"

QUIZ_STATUSES = (DRAFT, SCHEDULED, AVAILABLE, CLOSED, ARCHIVED)

#: Questions and settings may change only here (BR-QZ-005).
EDITABLE = frozenset({DRAFT, SCHEDULED})

# -- attempt lifecycle -------------------------------------------------------
IN_PROGRESS = "in_progress"
SUBMITTED = "submitted"
AUTO_SUBMITTED = "auto_submitted"
EVALUATED = "evaluated"
RELEASED = "released"

ATTEMPT_STATUSES = (IN_PROGRESS, SUBMITTED, AUTO_SUBMITTED, EVALUATED, RELEASED)

#: Responses are frozen once an attempt leaves IN_PROGRESS (BR-QZ-016).
FINISHED = frozenset({SUBMITTED, AUTO_SUBMITTED, EVALUATED, RELEASED})

PROFESSOR = "professor"
STUDENT = "student"
SYSTEM = "system"         # time boundaries: open, close, auto-submit


class InvalidTransition(Exception):
    def __init__(self, kind: str, frm: str, to: str):
        super().__init__(f"Cannot move a {kind} from {frm!r} to {to!r}.")
        self.kind, self.frm, self.to = kind, frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor: str, kind: str, frm: str, to: str):
        super().__init__(f"A {actor} may not move a {kind} from {frm!r} to {to!r}.")
        self.actor = actor


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    actors: frozenset[str]


def _t(frm: str, to: str, *actors: str) -> Transition:
    return Transition(frm, to, frozenset(actors))


QUIZ_TRANSITIONS: tuple[Transition, ...] = (
    _t(DRAFT, SCHEDULED, PROFESSOR),        # publish with a future start
    _t(DRAFT, AVAILABLE, PROFESSOR),        # publish for immediate availability
    _t(SCHEDULED, DRAFT, PROFESSOR),        # unpublish before it opens
    _t(SCHEDULED, AVAILABLE, SYSTEM),       # start boundary reached
    _t(AVAILABLE, CLOSED, SYSTEM, PROFESSOR),
    _t(CLOSED, ARCHIVED, PROFESSOR),        # BR-QZ-023
    _t(DRAFT, ARCHIVED, PROFESSOR),
)

ATTEMPT_TRANSITIONS: tuple[Transition, ...] = (
    _t(IN_PROGRESS, SUBMITTED, STUDENT),
    _t(IN_PROGRESS, AUTO_SUBMITTED, SYSTEM),            # BR-QZ-017
    _t(SUBMITTED, EVALUATED, SYSTEM, PROFESSOR),        # BR-QZ-018, BR-QZ-019
    _t(AUTO_SUBMITTED, EVALUATED, SYSTEM, PROFESSOR),
    _t(EVALUATED, RELEASED, PROFESSOR),                 # BR-QZ-021
)

_INDEX = {
    "quiz": {(t.frm, t.to): t for t in QUIZ_TRANSITIONS},
    "attempt": {(t.frm, t.to): t for t in ATTEMPT_TRANSITIONS},
}


def resolve(kind: str, frm: str, to: str, actor: str) -> Transition:
    """The single lookup every status write goes through."""
    t = _INDEX[kind].get((frm, to))
    if t is None:
        raise InvalidTransition(kind, frm, to)
    if actor not in t.actors:
        raise ActorNotAllowed(actor, kind, frm, to)
    return t


def is_legal(kind: str, frm: str, to: str) -> bool:
    return (frm, to) in _INDEX[kind]


# -- time rules --------------------------------------------------------------

def is_open(status: str, opens_at: datetime, closes_at: datetime,
            now: datetime) -> bool:
    """A student may start only inside the configured window (BR-QZ-006)."""
    return status == AVAILABLE and opens_at <= now < closes_at


def attempt_deadline(started_at: datetime, duration_minutes: int,
                     closes_at: datetime) -> datetime:
    """The earlier of the time limit and the quiz closing (BR-QZ-007)."""
    return min(started_at + timedelta(minutes=duration_minutes), closes_at)


def publish_target(opens_at: datetime, now: datetime) -> str:
    """Where a publish lands: straight to AVAILABLE, or SCHEDULED to wait."""
    return AVAILABLE if opens_at <= now else SCHEDULED
