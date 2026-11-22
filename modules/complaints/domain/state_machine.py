"""CMS lifecycle transitions from the synchronized workflow STTs.

Generic defaults resolve ISS-CMS-007 (assignment starts work), ISS-CMS-008
(approved reopening returns to in_progress), and ISS-CMS-010 (verification is
required by default; when disabled, resolution closes the complaint).
Escalation is orthogonal to the complaint lifecycle (CW-CMS-03).
"""

from __future__ import annotations

from dataclasses import dataclass

SUBMITTED = "submitted"
IN_PROGRESS = "in_progress"
RESOLVED = "resolved"
REJECTED = "rejected"
CLOSED = "closed"
COMPLAINANT = "complainant"
HANDLER = "handler"
SUPERVISOR = "supervisor"
SYSTEM = "system"


class InvalidTransition(Exception):
    pass


class ActorNotAllowed(Exception):
    pass


class GuardFailed(Exception):
    pass


@dataclass(frozen=True)
class Transition:
    source: str
    event: str
    actor: str
    target: str
    guard: str = ""


TRANSITIONS = (
    Transition(SUBMITTED, "start", HANDLER, IN_PROGRESS),
    Transition(IN_PROGRESS, "resolve", HANDLER, RESOLVED, "resolution_details"),
    Transition(SUBMITTED, "resolve", HANDLER, RESOLVED, "resolution_details"),
    Transition(IN_PROGRESS, "reject", HANDLER, REJECTED, "rejection_reason"),
    Transition(SUBMITTED, "reject", HANDLER, REJECTED, "rejection_reason"),
    Transition(RESOLVED, "verify_user", COMPLAINANT, CLOSED, "user_verification_required"),
    Transition(
        RESOLVED, "verify_supervisor", SUPERVISOR, CLOSED, "supervisor_verification_required"
    ),
)
_INDEX = {(t.source, t.event): t for t in TRANSITIONS}


def resolve(
    source: str, event: str, actor: str, *, guards: frozenset[str] = frozenset()
) -> Transition:
    transition = _INDEX.get((source, event))
    if transition is None:
        raise InvalidTransition(f"Event {event!r} is not allowed from {source!r}.")
    if transition.actor != actor:
        raise ActorNotAllowed(f"Actor {actor!r} cannot perform {event!r}.")
    if transition.guard and transition.guard not in guards:
        raise GuardFailed(f"Transition requires {transition.guard!r}.")
    return transition


def transitions_for(source: str, actor: str | None = None) -> tuple[Transition, ...]:
    return tuple(
        t for t in TRANSITIONS if t.source == source and (actor is None or t.actor == actor)
    )
