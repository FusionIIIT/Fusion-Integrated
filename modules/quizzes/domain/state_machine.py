"""Quiz and attempt state machines (CW-QZ-01, CW-QZ-02).

Declarative tables of legal moves. Pure Python, so the rules test with no DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta

DRAFT = "draft"
SCHEDULED = "scheduled"
AVAILABLE = "available"
CLOSED = "closed"
QUIZ_STATUSES = (DRAFT, SCHEDULED, AVAILABLE, CLOSED)

IN_PROGRESS = "in_progress"
SUBMITTED = "submitted"
AUTO_SUBMITTED = "auto_submitted"
ATTEMPT_STATUSES = (IN_PROGRESS, SUBMITTED, AUTO_SUBMITTED)

PROFESSOR = "professor"
STUDENT = "student"
SYSTEM = "system"         # time boundaries: open, close, auto-submit

QUIZ_TRANSITIONS = {
    (DRAFT, SCHEDULED): {PROFESSOR},          # publish with a future start
    (DRAFT, AVAILABLE): {PROFESSOR},          # publish for immediate availability
    (SCHEDULED, AVAILABLE): {SYSTEM},         # start boundary reached
    (AVAILABLE, CLOSED): {SYSTEM},            # closing boundary reached
}

ATTEMPT_TRANSITIONS = {
    (IN_PROGRESS, SUBMITTED): {STUDENT},
    (IN_PROGRESS, AUTO_SUBMITTED): {SYSTEM},  # BR-QZ-017
}

_TABLES = {"quiz": QUIZ_TRANSITIONS, "attempt": ATTEMPT_TRANSITIONS}


class InvalidTransition(Exception):
    pass


def check(kind: str, frm: str, to: str, actor: str) -> None:
    """The single gate every status write goes through."""
    actors = _TABLES[kind].get((frm, to))
    if actors is None:
        raise InvalidTransition(f"Cannot move a {kind} from {frm!r} to {to!r}.")
    if actor not in actors:
        raise InvalidTransition(f"A {actor} may not move a {kind} to {to!r}.")


def is_open(status: str, opens_at: datetime, closes_at: datetime,
            now: datetime) -> bool:
    """A student may start only inside the configured window (BR-QZ-006)."""
    return status == AVAILABLE and opens_at <= now < closes_at


def attempt_deadline(started_at: datetime, duration_minutes: int,
                     closes_at: datetime) -> datetime:
    """The earlier of the time limit and the quiz closing (BR-QZ-007)."""
    return min(started_at + timedelta(minutes=duration_minutes), closes_at)


def publish_target(opens_at: datetime, now: datetime) -> str:
    return AVAILABLE if opens_at <= now else SCHEDULED
