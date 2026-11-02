"""Visit-request state machine (pure Python).

Encodes the State-Transition Tables of BW-VMS-01, 02, 03, 06, 07, 08 and 22 (SRS 05).
Request-level states only: the SRS "Pass Active" / "On-site" states belong to the pass and
the visit log, so a request is ``approved`` from the moment its pass is issued until
``complete`` (check-out) moves it to ``completed`` (BR-105).

``cancelled`` is deliberately not a state (decision D-4).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

# --- kinds -------------------------------------------------------------------------------
PRE_REGISTERED, WALK_IN = "pre_registered", "walk_in"
KINDS = (PRE_REGISTERED, WALK_IN)

# --- states ------------------------------------------------------------------------------
#: Pseudo-state: the request does not exist yet ("Not Submitted"/"Not Registered"). Never stored.
NOT_SUBMITTED = "not_submitted"
PENDING = "pending"
AWAITING_ADMIN = "awaiting_admin"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
COMPLETED = "completed"

STATES = (PENDING, AWAITING_ADMIN, APPROVED, REJECTED, EXPIRED, COMPLETED)
TERMINAL = frozenset({REJECTED, EXPIRED, COMPLETED})

# --- events ------------------------------------------------------------------------------
SUBMIT = "submit"
HOST_APPROVE = "host_approve"
HOST_REJECT = "host_reject"
AUTO_EXPIRE = "auto_expire"
ADMIN_APPROVE_CONTINGENCY = "admin_approve_contingency"
ADMIN_REJECT_CONTINGENCY = "admin_reject_contingency"
URGENT_APPROVE = "urgent_approve"
URGENT_REJECT = "urgent_reject"
COMPLETE = "complete"

EVENTS = (SUBMIT, HOST_APPROVE, HOST_REJECT, AUTO_EXPIRE, ADMIN_APPROVE_CONTINGENCY,
          ADMIN_REJECT_CONTINGENCY, URGENT_APPROVE, URGENT_REJECT, COMPLETE)

# --- actors ------------------------------------------------------------------------------
VISITOR, HOST, ADMIN, SECURITY, SYSTEM = "visitor", "host", "admin", "security", "system"
ACTORS = (VISITOR, HOST, ADMIN, SECURITY, SYSTEM)

#: Facts a guard may read, all known before the move is made.
#: urgent          - pre-registration violates the advance window (BR-202/203)
#: bypass_approval - active pre-authorization or VIP override covers the visit (BR-195/197)
#: host_available  - walk-in host can be reached (BR-049/050)
FLAGS = ("urgent", "bypass_approval", "host_available")


class InvalidTransition(Exception):
    def __init__(self, kind: str, frm: str, event: str, actor: str):
        super().__init__(f"A {kind} request in {frm!r} has no {event!r} move for {actor!r}.")
        self.kind, self.frm, self.event, self.actor = kind, frm, event, actor


class AmbiguousTransition(Exception):
    """More than one row matched: the table is wrong, never the caller."""


@dataclass(frozen=True)
class Transition:
    kind: str
    frm: str
    event: str
    actor: str
    to: str
    when: tuple[tuple[str, bool], ...] = ()
    rows: str = ""  # SRS state-transition-table row(s)

    def matches(self, flags: Mapping[str, bool]) -> bool:
        return all(bool(flags.get(name, False)) is want for name, want in self.when)


def _t(kind, frm, event, actor, to, rows="", **when) -> Transition:
    return Transition(kind, frm, event, actor, to, tuple(sorted(when.items())), rows)


TABLE: tuple[Transition, ...] = (
    # --- pre-registered: BW-VMS-01/02/03/22 (+ BW-VMS-04/05 bypass, BR-195/197) ---
    _t(PRE_REGISTERED, NOT_SUBMITTED, SUBMIT, VISITOR, PENDING, "BW-01 R1; BW-02 R1; BW-03 R1",
       urgent=False, bypass_approval=False),
    _t(PRE_REGISTERED, NOT_SUBMITTED, SUBMIT, VISITOR, AWAITING_ADMIN, "BW-22 R1",
       urgent=True, bypass_approval=False),
    _t(PRE_REGISTERED, NOT_SUBMITTED, SUBMIT, VISITOR, APPROVED, "BW-04 R2; BW-05 R2",
       bypass_approval=True),
    _t(PRE_REGISTERED, PENDING, HOST_APPROVE, HOST, APPROVED, "BW-01 R2; BW-22 R3"),
    _t(PRE_REGISTERED, PENDING, HOST_REJECT, HOST, REJECTED, "BW-02 R2"),
    _t(PRE_REGISTERED, PENDING, AUTO_EXPIRE, SYSTEM, EXPIRED, "BW-03 R2"),
    _t(PRE_REGISTERED, AWAITING_ADMIN, URGENT_APPROVE, ADMIN, PENDING, "BW-22 R2"),
    _t(PRE_REGISTERED, AWAITING_ADMIN, URGENT_REJECT, ADMIN, REJECTED, "UC-035 reject"),
    _t(PRE_REGISTERED, APPROVED, COMPLETE, SECURITY, COMPLETED, "BW-01 R4; BW-22 R5"),
    _t(PRE_REGISTERED, APPROVED, COMPLETE, SYSTEM, COMPLETED, "BR-101 auto check-out"),
    # --- walk-in: BW-VMS-06/07/08 ---
    _t(WALK_IN, NOT_SUBMITTED, SUBMIT, SECURITY, PENDING, "BW-06 R1; BW-08 R1", host_available=True),
    _t(WALK_IN, NOT_SUBMITTED, SUBMIT, SECURITY, AWAITING_ADMIN, "BW-07 R1", host_available=False),
    _t(WALK_IN, PENDING, HOST_APPROVE, HOST, APPROVED, "BW-06 R2"),
    _t(WALK_IN, PENDING, HOST_REJECT, HOST, REJECTED, "BW-08 R2"),
    # BR-062 is stated for any pending request; BW-03 only draws the pre-registered case.
    _t(WALK_IN, PENDING, AUTO_EXPIRE, SYSTEM, EXPIRED, "BR-062"),
    _t(WALK_IN, AWAITING_ADMIN, ADMIN_APPROVE_CONTINGENCY, ADMIN, APPROVED, "BW-07 R2"),
    _t(WALK_IN, AWAITING_ADMIN, ADMIN_REJECT_CONTINGENCY, ADMIN, REJECTED, "UC-033 reject"),
    _t(WALK_IN, APPROVED, COMPLETE, SECURITY, COMPLETED, "BW-06 R4; BW-07 R4"),
    _t(WALK_IN, APPROVED, COMPLETE, SYSTEM, COMPLETED, "BR-101 auto check-out"),
)


def resolve(kind: str, frm: str, event: str, actor: str,
            flags: Mapping[str, bool] | None = None) -> Transition:
    """Return the single matching row, or raise InvalidTransition (none) / AmbiguousTransition."""
    flags = flags or {}
    hits = [t for t in TABLE
            if (t.kind, t.frm, t.event, t.actor) == (kind, frm, event, actor) and t.matches(flags)]
    if not hits:
        raise InvalidTransition(kind, frm, event, actor)
    if len(hits) > 1:
        raise AmbiguousTransition(f"{len(hits)} rows match {kind}/{frm}/{event}/{actor}")
    return hits[0]


def next_state(kind: str, frm: str, event: str, actor: str,
               flags: Mapping[str, bool] | None = None) -> str:
    return resolve(kind, frm, event, actor, flags).to


def legal_events(kind: str, frm: str, actor: str | None = None) -> frozenset[str]:
    return frozenset(t.event for t in TABLE
                     if t.kind == kind and t.frm == frm and (actor is None or t.actor == actor))
