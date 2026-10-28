"""The ELM request lifecycle, as a declarative table (ELM Problem Statement §6-10).

One formalism, edges stated once so "which move is legal" and "who may make it"
have exactly one answer each. Pure Python — no Django import.

Wireflow summarised:
  pending --withdraw--> withdrawn                       (any time before final)
  pending --recommend--> recommended  --sanction--> sanctioned
  pending --not_recommend--> not_recommended --sanction--> sanctioned|rejected
  pending --(CL/RH: unit head decides)--> sanctioned|rejected
  sanctioned --cancel_request--> cancellation_pending --approve--> cancelled
                                                     \\--reject--> sanctioned
"""
from __future__ import annotations

from dataclasses import dataclass, field

PENDING = "pending"
RECOMMENDED = "recommended"
NOT_RECOMMENDED = "not_recommended"
SANCTIONED = "sanctioned"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLATION_PENDING = "cancellation_pending"
CANCELLED = "cancelled"

#: extension/resumption are tracked as sub-states on a sanctioned application
EXTENSION_PENDING = "extension_pending"
RESUMPTION_PENDING = "resumption_pending"

TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED})
#: Pre-final-approval states where withdraw is still available.
WITHDRAWABLE = frozenset({PENDING, RECOMMENDED, NOT_RECOMMENDED})

APPLICANT = "applicant"
UNIT_HEAD = "unit_head"
SANCTION_AUTHORITY = "sanctioning_authority"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move a leave request from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor: str, frm: str, to: str):
        super().__init__(f"A {actor} may not move a request from {frm!r} to {to!r}.")


class GuardFailed(Exception):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


TRANSITIONS: tuple[Transition, ...] = (
    # -- applicant-driven, pending only ------------------------------------
    Transition(PENDING, RECOMMENDED, "leave_management.leave.review",
               frozenset({UNIT_HEAD}), ("has_substitute_consent",)),
    Transition(PENDING, NOT_RECOMMENDED, "leave_management.leave.review",
               frozenset({UNIT_HEAD}), ()),
    # CL/RH are decided outright by the Unit Head (final authority).
    Transition(PENDING, SANCTIONED, "leave_management.leave.sanction",
               frozenset({UNIT_HEAD, SANCTION_AUTHORITY}), ("has_balance",)),
    Transition(PENDING, REJECTED, "leave_management.leave.sanction",
               frozenset({UNIT_HEAD, SANCTION_AUTHORITY}), ()),
    Transition(PENDING, WITHDRAWN, "leave_management.leave.withdraw",
               frozenset({APPLICANT}), ()),

    # -- post-recommendation -----------------------------------------------
    Transition(RECOMMENDED, SANCTIONED, "leave_management.leave.sanction",
               frozenset({SANCTION_AUTHORITY}), ("has_balance",)),
    Transition(RECOMMENDED, REJECTED, "leave_management.leave.sanction",
               frozenset({SANCTION_AUTHORITY}), ()),
    Transition(RECOMMENDED, WITHDRAWN, "leave_management.leave.withdraw",
               frozenset({APPLICANT}), ()),

    Transition(NOT_RECOMMENDED, SANCTIONED, "leave_management.leave.sanction",
               frozenset({SANCTION_AUTHORITY}), ("has_balance",)),
    Transition(NOT_RECOMMENDED, REJECTED, "leave_management.leave.sanction",
               frozenset({SANCTION_AUTHORITY}), ()),
    Transition(NOT_RECOMMENDED, WITHDRAWN, "leave_management.leave.withdraw",
               frozenset({APPLICANT}), ()),

    # -- pre-start cancellation of an approved leave (§8) ------------------
    Transition(SANCTIONED, CANCELLATION_PENDING,
               "leave_management.leave.cancel", frozenset({APPLICANT}),
               ("before_start",)),
    Transition(CANCELLATION_PENDING, CANCELLED,
               "leave_management.leave.sanction",
               frozenset({UNIT_HEAD, SANCTION_AUTHORITY}),
               ("cancellation_approved",)),
    Transition(CANCELLATION_PENDING, SANCTIONED,
               "leave_management.leave.sanction",
               frozenset({UNIT_HEAD, SANCTION_AUTHORITY}), ()),

    # -- extension (§9) and resumption (§10) -------------------------------
    Transition(SANCTIONED, EXTENSION_PENDING,
               "leave_management.leave.extension", frozenset({APPLICANT}), ()),
    Transition(EXTENSION_PENDING, SANCTIONED,
               "leave_management.leave.sanction",
               frozenset({UNIT_HEAD, SANCTION_AUTHORITY}),
               ("has_balance", "has_substitute_consent")),
    Transition(EXTENSION_PENDING, SANCTIONED,   # rejected: original stands
               "leave_management.leave.sanction",
               frozenset({UNIT_HEAD, SANCTION_AUTHORITY}), ()),
    Transition(SANCTIONED, RESUMPTION_PENDING,
               "leave_management.leave.resumption", frozenset({APPLICANT}), ()),
    Transition(RESUMPTION_PENDING, SANCTIONED,
               "leave_management.leave.sanction",
               frozenset({UNIT_HEAD, SANCTION_AUTHORITY}), ()),
)


def _find(frm: str, to: str) -> Transition | None:
    for t in TRANSITIONS:
        if t.frm == frm and t.to == to:
            return t
    return None


def validate_transition(frm: str, to: str, *, actor: str,
                        permissions: frozenset[str] | set[str]) -> Transition:
    """Raise if the move is not legal for this actor. Having the permission is
    necessary but not sufficient — the actor *kind* must also match the edge."""
    t = _find(frm, to)
    if t is None:
        raise InvalidTransition(frm, to)
    if actor not in t.actors:
        raise ActorNotAllowed(actor, frm, to)
    if t.permission not in permissions and "*" not in permissions:
        raise GuardFailed("permission",
                          f"{actor} lacks {t.permission!r} for {frm}->{to}.")
    return t


def may_withdraw(status: str) -> bool:
    return status in WITHDRAWABLE
