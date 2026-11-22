"""Declarative transition tables: a move that is not listed cannot be expressed."""

from __future__ import annotations

from dataclasses import dataclass

from modules.department.domain.errors import ActorNotAllowed, InvalidTransition
from modules.department.domain.roles import DEPT_ADMIN, FACULTY, HOD, STUDENT

NONE = ""

# -- stock request (BW-DEPT-01, BW-DEPT-02, CW-DEPT-01) --------------------------
STOCK_PENDING = "pending_hod"
STOCK_APPROVED = "approved"
STOCK_REJECTED = "rejected"
STOCK_ISSUED = "issued"

# -- feedback (BW-DEPT-03, BW-DEPT-04, CW-DEPT-02) -------------------------------
FEEDBACK_NEW = "new"
FEEDBACK_UNDER_REVIEW = "under_review"
FEEDBACK_RESOLVED = "resolved"
FEEDBACK_CLOSED = "closed"

# -- official department change (BW-DEPT-05, BW-DEPT-06, CW-DEPT-03) -------------
CHANGE_PENDING = "pending"
CHANGE_APPROVED = "approved"
CHANGE_REJECTED = "rejected"


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]


STOCK_TRANSITIONS: tuple[Transition, ...] = (
    Transition(NONE, STOCK_PENDING, "department.stock_request.create", frozenset({FACULTY})),
    Transition(STOCK_PENDING, STOCK_APPROVED, "department.stock_request.approve", frozenset({HOD})),
    Transition(STOCK_PENDING, STOCK_REJECTED, "department.stock_request.approve", frozenset({HOD})),
    Transition(
        STOCK_APPROVED, STOCK_ISSUED, "department.stock_issue.create", frozenset({DEPT_ADMIN})
    ),
)

FEEDBACK_TRANSITIONS: tuple[Transition, ...] = (
    Transition(NONE, FEEDBACK_NEW, "department.feedback.create", frozenset({STUDENT, FACULTY})),
    Transition(
        FEEDBACK_NEW, FEEDBACK_UNDER_REVIEW, "department.feedback.review", frozenset({DEPT_ADMIN})
    ),
    Transition(
        FEEDBACK_UNDER_REVIEW,
        FEEDBACK_RESOLVED,
        "department.feedback_resolution.create",
        frozenset({DEPT_ADMIN, HOD}),
    ),
    Transition(
        FEEDBACK_UNDER_REVIEW,
        FEEDBACK_CLOSED,
        "department.feedback_resolution.create",
        frozenset({DEPT_ADMIN, HOD}),
    ),
)

OFFICIAL_CHANGE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(NONE, CHANGE_PENDING, "department.official_change.create", frozenset({DEPT_ADMIN})),
    Transition(
        CHANGE_PENDING, CHANGE_APPROVED, "department.official_change.approve", frozenset({HOD})
    ),
    Transition(
        CHANGE_PENDING, CHANGE_REJECTED, "department.official_change.approve", frozenset({HOD})
    ),
)

MACHINES = {
    "stock request": STOCK_TRANSITIONS,
    "feedback": FEEDBACK_TRANSITIONS,
    "official change": OFFICIAL_CHANGE_TRANSITIONS,
}

_INDEX = {name: {(t.frm, t.to): t for t in table} for name, table in MACHINES.items()}


def resolve(machine: str, frm: str, to: str, actor: str | None) -> Transition:
    """The single lookup every state change goes through."""
    t = _INDEX[machine].get((frm, to))
    if t is None:
        raise InvalidTransition(machine, frm, to)
    if actor not in t.actors:
        raise ActorNotAllowed(machine, actor, frm, to)
    return t


def states(machine: str) -> frozenset[str]:
    table = MACHINES[machine]
    return frozenset({t.frm for t in table} | {t.to for t in table})


def terminal(machine: str) -> frozenset[str]:
    table = MACHINES[machine]
    return frozenset({t.to for t in table} - {t.frm for t in table})
