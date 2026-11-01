"""Stock-request and feedback lifecycles (WF: BW-DEPT-01/02, CW-DEPT-01,
BW-DEPT-03/04, CW-DEPT-02).

Declarative tables, so an illegal move is impossible to express rather than
merely rejected, and "who may do this?" has one answer per edge. Pure Python.
"""
from __future__ import annotations

from dataclasses import dataclass

# -- stock request ------------------------------------------------------------
PENDING_HOD = "pending_hod"
APPROVED = "approved"
REJECTED = "rejected"
ISSUED = "issued"

STOCK_TERMINAL = frozenset({REJECTED, ISSUED})

# -- feedback -----------------------------------------------------------------
NEW = "new"
UNDER_REVIEW = "under_review"
RESOLVED = "resolved"
CLOSED = "closed"

FEEDBACK_TERMINAL = frozenset({RESOLVED, CLOSED})


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, permission: str):
        super().__init__(f"This action needs {permission}.")
        self.permission = permission


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str


STOCK_TRANSITIONS: tuple[Transition, ...] = (
    # BR-DEPT-006: only the HOD decides.
    Transition(PENDING_HOD, APPROVED, "dept.stock_request.decide"),
    Transition(PENDING_HOD, REJECTED, "dept.stock_request.decide"),
    # BR-DEPT-007: Dept_Admin issues, and only an approved request.
    Transition(APPROVED, ISSUED, "dept.stock_request.issue"),
)

FEEDBACK_TRANSITIONS: tuple[Transition, ...] = (
    # BR-DEPT-018: Dept_Admin's initial review comes first.
    Transition(NEW, UNDER_REVIEW, "dept.feedback.review"),
    # BR-DEPT-009: Dept_Admin or HOD may dispose of it.
    Transition(UNDER_REVIEW, RESOLVED, "dept.feedback.review"),
    Transition(UNDER_REVIEW, CLOSED, "dept.feedback.review"),
    Transition(UNDER_REVIEW, RESOLVED, "dept.feedback.resolve"),
    Transition(UNDER_REVIEW, CLOSED, "dept.feedback.resolve"),
)


def validate_transition(table: tuple[Transition, ...], frm: str, to: str,
                        permissions: frozenset[str] | set[str]) -> Transition:
    """The edge must exist (InvalidTransition) and the actor must hold the
    permission of at least one edge that connects the two (ActorNotAllowed)."""
    edges = [t for t in table if t.frm == frm and t.to == to]
    if not edges:
        raise InvalidTransition(frm, to)
    for edge in edges:
        if edge.permission in permissions:
            return edge
    raise ActorNotAllowed(edges[0].permission)
