"""The leave request state machine (CW-EL-01..04).

Declarative, like placement's: an illegal move has no row, so it cannot be
expressed. Cancellation, extension and resumption are requests of their own
that reuse the same review states.
"""
from __future__ import annotations

from dataclasses import dataclass

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_SANCTION = "awaiting_sanction"
AWAITING_DIRECTOR = "awaiting_director"
AWAITING_RESUMPTION_REVIEW = "awaiting_resumption_review"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"
RESUMPTION_REVIEWED = "resumption_reviewed"

PENDING = frozenset({AWAITING_SUBSTITUTE, APPLICANT_ACTION, AWAITING_UNIT_HEAD,
                     AWAITING_ESTABLISHMENT, AWAITING_SANCTION, AWAITING_DIRECTOR})
TERMINAL = frozenset({APPROVED, REJECTED, WITHDRAWN, CANCELLED,
                      RESUMPTION_REVIEWED})

EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
AUTHORITY = "authority"
DIRECTOR = "director"
SYSTEM = "system"

P_CREATE = "elm.leave_request.create"
P_REVIEW = "elm.leave_request.review"
P_ASSIGN = "elm.leave_request.assign"
P_APPROVE = "elm.leave_request.approve"
P_SYSTEM = "elm.leave_account.update"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"A request cannot move from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor: str, frm: str, to: str):
        super().__init__(f"A {actor} may not move a request from {frm!r} to {to!r}.")
        self.actor, self.frm, self.to = actor, frm, to


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    actor: str
    permission: str


TRANSITIONS: tuple[Transition, ...] = (
    # CW-EL-01 rows 1-3 (EL-UC-001, EL-UC-009), and CW-EL-04 submission
    Transition(DRAFT, AWAITING_SUBSTITUTE, EMPLOYEE, P_CREATE),
    Transition(DRAFT, AWAITING_DIRECTOR, EMPLOYEE, P_CREATE),
    Transition(DRAFT, AWAITING_UNIT_HEAD, EMPLOYEE, P_CREATE),
    Transition(DRAFT, AWAITING_RESUMPTION_REVIEW, EMPLOYEE, P_CREATE),
    # rows 4-7 (EL-UC-002, EL-UC-019)
    Transition(AWAITING_SUBSTITUTE, AWAITING_DIRECTOR, SUBSTITUTE, P_CREATE),
    Transition(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, SUBSTITUTE, P_CREATE),
    Transition(AWAITING_SUBSTITUTE, APPLICANT_ACTION, SUBSTITUTE, P_CREATE),
    Transition(APPLICANT_ACTION, AWAITING_SUBSTITUTE, EMPLOYEE, P_CREATE),
    # rows 8-11 (EL-UC-003)
    Transition(AWAITING_UNIT_HEAD, APPROVED, UNIT_HEAD, P_REVIEW),
    Transition(AWAITING_UNIT_HEAD, REJECTED, UNIT_HEAD, P_REVIEW),
    Transition(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, UNIT_HEAD, P_REVIEW),
    Transition(AWAITING_UNIT_HEAD, AWAITING_SANCTION, UNIT_HEAD, P_REVIEW),
    # row 12 (EL-UC-004)
    Transition(AWAITING_ESTABLISHMENT, AWAITING_SANCTION, ESTABLISHMENT, P_ASSIGN),
    # rows 13-16 (EL-UC-005)
    Transition(AWAITING_SANCTION, APPROVED, AUTHORITY, P_APPROVE),
    Transition(AWAITING_SANCTION, REJECTED, AUTHORITY, P_APPROVE),
    Transition(AWAITING_DIRECTOR, APPROVED, DIRECTOR, P_APPROVE),
    Transition(AWAITING_DIRECTOR, REJECTED, DIRECTOR, P_APPROVE),
    # row 17 (EL-UC-007)
    *(Transition(s, WITHDRAWN, EMPLOYEE, P_CREATE) for s in sorted(PENDING)),
    # CW-EL-02: an approved cancellation closes the original leave
    Transition(APPROVED, CANCELLED, SYSTEM, P_SYSTEM),
    # CW-EL-04 (EL-UC-011)
    Transition(AWAITING_RESUMPTION_REVIEW, RESUMPTION_REVIEWED, AUTHORITY,
               P_APPROVE),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor: str) -> Transition:
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if t.actor != actor:
        raise ActorNotAllowed(actor, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


#: Which reviewer acts at each review state, and with which permission.
REVIEW_STAGE = {
    AWAITING_UNIT_HEAD: (UNIT_HEAD, P_REVIEW),
    AWAITING_ESTABLISHMENT: (ESTABLISHMENT, P_ASSIGN),
    AWAITING_SANCTION: (AUTHORITY, P_APPROVE),
    AWAITING_DIRECTOR: (DIRECTOR, P_APPROVE),
    AWAITING_RESUMPTION_REVIEW: (AUTHORITY, P_APPROVE),
}


# -- approval chain -------------------------------------------------------------
#: Each chain stage, the request state while it is active, and the permission.
STAGE_STATE = {
    SUBSTITUTE: AWAITING_SUBSTITUTE,
    UNIT_HEAD: AWAITING_UNIT_HEAD,
    ESTABLISHMENT: AWAITING_ESTABLISHMENT,
    AUTHORITY: AWAITING_SANCTION,
    DIRECTOR: AWAITING_DIRECTOR,
}
STAGE_PERMISSION = {
    SUBSTITUTE: P_CREATE,
    UNIT_HEAD: P_REVIEW,
    ESTABLISHMENT: P_ASSIGN,
    AUTHORITY: P_APPROVE,
    DIRECTOR: P_APPROVE,
}


def build_chain(*, unit_head_final: bool, has_substitute: bool,
                is_director: bool, has_establishment: bool,
                resumption: bool = False) -> list[str]:
    """The whole route, fixed at submission (CW-EL-01..04)."""
    if resumption:
        return [DIRECTOR if is_director else AUTHORITY]
    chain = [SUBSTITUTE] if has_substitute else []
    if is_director:
        return [*chain, DIRECTOR]
    chain.append(UNIT_HEAD)
    if not unit_head_final:
        chain += [ESTABLISHMENT] if has_establishment else []
        chain.append(AUTHORITY)
    return chain
