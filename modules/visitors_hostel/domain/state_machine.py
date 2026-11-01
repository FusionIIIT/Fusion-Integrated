"""Declarative booking lifecycle based on the VHMS workflow artifacts."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import ActorNotAllowed, InvalidTransition

PENDING = "pending"
FORWARDED = "forwarded"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLATION_REQUESTED = "cancellation_requested"
CANCELLED = "cancelled"
ROOM_ALLOTTED = "room_allotted"
CHECKED_IN = "checked_in"
CHECKED_OUT = "checked_out"

INDENTER = "indenter"
CARETAKER = "caretaker"
IN_CHARGE = "vh_in_charge"


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    actor: str
    permission: str


TRANSITIONS = (
    Transition(PENDING, FORWARDED, CARETAKER, "visitor_hostel.booking.review"),
    Transition(PENDING, REJECTED, CARETAKER, "visitor_hostel.booking.review"),
    Transition(FORWARDED, APPROVED, IN_CHARGE, "visitor_hostel.booking.decide"),
    Transition(FORWARDED, REJECTED, IN_CHARGE, "visitor_hostel.booking.decide"),
    Transition(PENDING, CANCELLATION_REQUESTED, INDENTER,
               "visitor_hostel.booking.cancel_self"),
    Transition(FORWARDED, CANCELLATION_REQUESTED, INDENTER,
               "visitor_hostel.booking.cancel_self"),
    Transition(APPROVED, CANCELLATION_REQUESTED, INDENTER,
               "visitor_hostel.booking.cancel_self"),
    Transition(CANCELLATION_REQUESTED, CANCELLED, CARETAKER,
               "visitor_hostel.booking.review"),
    Transition(APPROVED, ROOM_ALLOTTED, CARETAKER,
               "visitor_hostel.room.manage"),
    Transition(ROOM_ALLOTTED, CHECKED_IN, CARETAKER,
               "visitor_hostel.stay.manage"),
    Transition(CHECKED_IN, CHECKED_OUT, CARETAKER,
               "visitor_hostel.stay.manage"),
)

_INDEX = {(t.source, t.target): t for t in TRANSITIONS}


def resolve(source: str, target: str, actor: str) -> Transition:
    transition = _INDEX.get((source, target))
    if transition is None:
        raise InvalidTransition(f"Cannot move booking from {source!r} to {target!r}.")
    if transition.actor != actor:
        raise ActorNotAllowed(
            f"A {actor!r} cannot move booking from {source!r} to {target!r}.")
    return transition


def allowed_targets(source: str, actor: str | None = None) -> tuple[str, ...]:
    return tuple(sorted(t.target for t in TRANSITIONS
                        if t.source == source and (actor is None or t.actor == actor)))
