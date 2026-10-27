"""Leave state machine (BR-EL-015..023, CW-EL-01..04)."""
from __future__ import annotations

from dataclasses import dataclass, field

DRAFT = "draft"
AWAITING_SUB = "awaiting_substitute"
UNIT_HEAD = "unit_head_queue"
ESTAB = "establishment"
FINAL = "final_decision"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"

TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED})

EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNITHEAD = "unit_head"
ESTABLISHMENT = "establishment"
AUTHORITY = "authority"
DIRECTOR = "director"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move leave from '{frm}' to '{to}'.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(f"Actor of kind '{actor_kind}' is not authorized to transition leave from '{frm}' to '{to}'.")
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


TRANSITIONS: tuple[Transition, ...] = (
    # Initial submissions
    Transition(DRAFT, AWAITING_SUB, "elm.leave.create",
               frozenset({EMPLOYEE, SYSTEM}), ("has_balance",)),
    Transition(DRAFT, UNIT_HEAD, "elm.leave.create",
               frozenset({EMPLOYEE, SYSTEM}), ("has_balance",)),
    Transition(DRAFT, FINAL, "elm.leave.self_sanction",
               frozenset({DIRECTOR})),
    Transition(DRAFT, APPROVED, "elm.leave.self_sanction",
               frozenset({DIRECTOR})),

    # Substitute stage (BR-EL-014, BR-EL-015)
    Transition(AWAITING_SUB, UNIT_HEAD, "elm.leave.create",
               frozenset({SUBSTITUTE, SYSTEM, EMPLOYEE}), ("substitute_accepted",)),
    Transition(AWAITING_SUB, REJECTED, "elm.leave.create",
               frozenset({SUBSTITUTE, SYSTEM}), ("substitute_declined",)),

    # Unit head stage (BR-EL-016 for CL/RH, BR-EL-017 for higher leaves)
    Transition(UNIT_HEAD, APPROVED, "elm.leave.decide",
               frozenset({UNITHEAD, AUTHORITY, DIRECTOR})),
    Transition(UNIT_HEAD, ESTAB, "elm.leave.recommend",
               frozenset({UNITHEAD})),
    Transition(UNIT_HEAD, FINAL, "elm.leave.recommend",
               frozenset({UNITHEAD})),
    Transition(UNIT_HEAD, REJECTED, "elm.leave.recommend",
               frozenset({UNITHEAD}), ("has_reason",)),

    # Establishment stage (BR-EL-019)
    Transition(ESTAB, FINAL, "elm.leave.verify",
               frozenset({ESTABLISHMENT})),
    Transition(ESTAB, REJECTED, "elm.leave.verify",
               frozenset({ESTABLISHMENT}), ("has_reason",)),

    # Final authority sanction (BR-EL-018, BR-EL-019)
    Transition(FINAL, APPROVED, "elm.leave.decide",
               frozenset({AUTHORITY, DIRECTOR})),
    Transition(FINAL, REJECTED, "elm.leave.decide",
               frozenset({AUTHORITY, DIRECTOR}), ("has_reason",)),

    # Approved leave cancellation before start date (BR-EL-023)
    Transition(APPROVED, CANCELLED, "elm.leave.cancel",
               frozenset({EMPLOYEE, AUTHORITY, DIRECTOR})),

    # Immediate applicant withdrawal on any pending stage (BR-EL-022)
    *(Transition(s, WITHDRAWN, "elm.leave.withdraw",
                 frozenset({EMPLOYEE}))
      for s in (AWAITING_SUB, UNIT_HEAD, ESTAB, FINAL)),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted({t.to for t in TRANSITIONS
                   if t.frm == frm
                   and (actor_kind is None or actor_kind in t.actors)})
