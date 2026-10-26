"""States of a leave application and the legal moves between them (WF-EL-01..05)."""
from __future__ import annotations

from dataclasses import dataclass

from modules.elm.domain import leave_types as lt
from modules.elm.domain.errors import RuleViolation

AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE"
SUBSTITUTE_DECLINED = "SUBSTITUTE_DECLINED"
AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD"
AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT"
AWAITING_FINAL = "AWAITING_FINAL_SANCTION"
AWAITING_DIRECTOR = "AWAITING_DIRECTOR_SELF_SANCTION"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"
CANCELLED = "CANCELLED"
RESUMPTION_PENDING = "RESUMPTION_PENDING"
COMPLETED = "COMPLETED"

#: Waiting on somebody, and the employee may still withdraw (BR-EL-022).
PENDING = frozenset({AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINED, AWAITING_UNIT_HEAD,
                     AWAITING_ESTABLISHMENT, AWAITING_FINAL, AWAITING_DIRECTOR})
#: BR-EL-021: only before anyone has acted.
MODIFIABLE = frozenset({AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINED, AWAITING_UNIT_HEAD})
#: Holding days against the balance or the calendar (BR-EL-012).
ACTIVE = PENDING | {APPROVED, RESUMPTION_PENDING}
FINISHED = frozenset({REJECTED, WITHDRAWN, CANCELLED, COMPLETED})

EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT, SANCTION, DIRECTOR = (
    "employee", "substitute", "unit_head", "establishment", "sanction", "director")

#: Who owns the task in each waiting state; drives queues and SLA reminders.
TASK_OWNER = {
    AWAITING_SUBSTITUTE: SUBSTITUTE,
    AWAITING_UNIT_HEAD: UNIT_HEAD,
    AWAITING_ESTABLISHMENT: ESTABLISHMENT,
    AWAITING_FINAL: SANCTION,
    AWAITING_DIRECTOR: DIRECTOR,
    RESUMPTION_PENDING: UNIT_HEAD,
}


@dataclass(frozen=True)
class Move:
    frm: str
    to: str
    actor: str


MOVES = (
    Move(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, SUBSTITUTE),
    Move(AWAITING_SUBSTITUTE, AWAITING_DIRECTOR, SUBSTITUTE),
    Move(AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINED, SUBSTITUTE),
    Move(AWAITING_UNIT_HEAD, APPROVED, UNIT_HEAD),
    Move(AWAITING_UNIT_HEAD, REJECTED, UNIT_HEAD),
    Move(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, UNIT_HEAD),
    Move(AWAITING_UNIT_HEAD, AWAITING_FINAL, UNIT_HEAD),
    Move(AWAITING_ESTABLISHMENT, AWAITING_FINAL, ESTABLISHMENT),
    Move(AWAITING_FINAL, APPROVED, SANCTION),
    Move(AWAITING_FINAL, REJECTED, SANCTION),
    Move(AWAITING_DIRECTOR, APPROVED, DIRECTOR),
    Move(APPROVED, AWAITING_UNIT_HEAD, EMPLOYEE),
    Move(APPROVED, AWAITING_DIRECTOR, EMPLOYEE),
    Move(APPROVED, RESUMPTION_PENDING, EMPLOYEE),
    Move(RESUMPTION_PENDING, COMPLETED, UNIT_HEAD),
    Move(RESUMPTION_PENDING, APPROVED, UNIT_HEAD),
    Move(AWAITING_UNIT_HEAD, CANCELLED, UNIT_HEAD),
    Move(AWAITING_FINAL, CANCELLED, SANCTION),
    Move(AWAITING_DIRECTOR, CANCELLED, DIRECTOR),
    *(Move(s, WITHDRAWN, EMPLOYEE) for s in sorted(PENDING)),
    #: Withdrawing a cancellation request leaves the approved leave standing.
    *(Move(s, APPROVED, EMPLOYEE) for s in (
        AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_FINAL, AWAITING_DIRECTOR)),
)


def check_move(frm: str, to: str, actor: str) -> None:
    if not any(m.frm == frm and m.to == to and m.actor == actor for m in MOVES):
        raise RuleViolation(f"A {actor} cannot move a request from {frm} to {to}.", "WF-EL-01")


def first_state(*, substitute_required: bool, is_director: bool) -> str:
    """Where a valid new request lands (BR-EL-015, BR-EL-020)."""
    if substitute_required:
        return AWAITING_SUBSTITUTE
    return AWAITING_DIRECTOR if is_director else AWAITING_UNIT_HEAD


def after_substitute_accepts(is_director: bool) -> str:
    return AWAITING_DIRECTOR if is_director else AWAITING_UNIT_HEAD


def after_unit_head_recommendation(*, establishment_step: bool) -> str:
    return AWAITING_ESTABLISHMENT if establishment_step else AWAITING_FINAL


def unit_head_may_decide(leave_type: str) -> bool:
    return leave_type in lt.UNIT_HEAD_FINAL


def final_state(*, approved: bool, cancelling: bool) -> str:
    """Outcome of the last decision. A refused cancellation leaves the leave standing."""
    if cancelling:
        return CANCELLED if approved else APPROVED
    return APPROVED if approved else REJECTED
