"""The booking state machine (CW-VH-01, CW-VH-02, BW-VH-10).

A declarative table of legal moves, so an illegal transition is impossible to
express rather than merely rejected, and "who may do this?" has exactly one
answer per edge. Online and offline bookings share every edge (BR-VH-003);
offline is a flag on the row (BR-VH-005), not a separate lane.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from modules.visitor_hostel.domain import permissions as perms

PENDING = "pending"
FORWARDED = "forwarded"
APPROVED = "approved"
REJECTED = "rejected"
ROOM_ALLOTTED = "room_allotted"
CHECKED_IN = "checked_in"
CHECKED_OUT = "checked_out"
CANCELLED = "cancelled"

ALL_STATES = (PENDING, FORWARDED, APPROVED, REJECTED, ROOM_ALLOTTED,
              CHECKED_IN, CHECKED_OUT, CANCELLED)
TERMINAL = frozenset({REJECTED, CHECKED_OUT, CANCELLED})

#: "Booking exists (pre-arrival)" in BW-VH-07..09 — the states a cancellation may start from.
PRE_ARRIVAL = frozenset({PENDING, FORWARDED, APPROVED, ROOM_ALLOTTED})

#: Records a reassigned Caretaker inherits (BR-VH-049 pending, BR-VH-050 ongoing).
CARETAKER_PENDING = frozenset({PENDING})
CARETAKER_ONGOING = frozenset({FORWARDED, APPROVED, ROOM_ALLOTTED, CHECKED_IN})
#: Records a reassigned VH In-Charge inherits.
INCHARGE_PENDING = frozenset({FORWARDED})
INCHARGE_ONGOING = frozenset({APPROVED, ROOM_ALLOTTED, CHECKED_IN})

# Lanes. The service decides the lane from the operation, never from the request body.
INDENTER = "indenter"
CARETAKER = "caretaker"
INCHARGE = "incharge"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"A booking cannot move from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, lane: str, frm: str, to: str):
        super().__init__(f"A {lane} may not move a booking from {frm!r} to {to!r}.")
        self.lane, self.frm, self.to = lane, frm, to


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    use_case: str
    guards: tuple[str, ...] = field(default_factory=tuple)


TRANSITIONS: tuple[Transition, ...] = (
    # CW-VH-01 rows 3-4: Caretaker review and routing (UC-VH-003)
    Transition(PENDING, FORWARDED, perms.BOOKING_REVIEW, frozenset({CARETAKER}),
               "UC-VH-003"),
    Transition(PENDING, REJECTED, perms.BOOKING_REVIEW, frozenset({CARETAKER}),
               "UC-VH-003", ("has_reason",)),

    # CW-VH-01 rows 5-6: VH In-Charge decision (UC-VH-004)
    Transition(FORWARDED, APPROVED, perms.BOOKING_APPROVE, frozenset({INCHARGE}),
               "UC-VH-004"),
    Transition(FORWARDED, REJECTED, perms.BOOKING_APPROVE, frozenset({INCHARGE}),
               "UC-VH-004", ("has_reason",)),

    # BW-VH-10: the approved stay. Allotment only from Approved is BR-VH-012.
    Transition(APPROVED, ROOM_ALLOTTED, perms.ROOM_MANAGE, frozenset({CARETAKER}),
               "UC-VH-008"),
    Transition(ROOM_ALLOTTED, CHECKED_IN, perms.STAY_UPDATE, frozenset({CARETAKER}),
               "UC-VH-009"),
    Transition(CHECKED_IN, CHECKED_OUT, perms.STAY_UPDATE, frozenset({CARETAKER}),
               "UC-VH-021"),

    # CW-VH-02 row 4: Caretaker confirms an Indenter's cancellation (UC-VH-020)
    *(Transition(s, CANCELLED, perms.CANCELLATION_APPROVE, frozenset({CARETAKER}),
                 "UC-VH-020", ("cancellation_requested",))
      for s in sorted(PRE_ARRIVAL)),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, lane: str | None = None) -> Transition:
    """The single lookup every status change goes through."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if lane is not None and lane not in t.actors:
        raise ActorNotAllowed(lane, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def permission_for(to: str, lane: str) -> str | None:
    """The code a lane needs to reach `to` from anywhere, so a missing grant is
    reported before a state mismatch — the more useful of the two refusals."""
    for t in TRANSITIONS:
        if t.to == to and lane in t.actors:
            return t.permission
    return None


def allowed_targets(frm: str, lane: str | None = None) -> list[str]:
    return sorted(t.to for t in TRANSITIONS
                  if t.frm == frm and (lane is None or lane in t.actors))
