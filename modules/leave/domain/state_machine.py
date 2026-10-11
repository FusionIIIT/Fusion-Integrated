"""Pure-Python leave request state machine.

NO Django imports allowed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

# Statuses
PENDING   = "pending"
APPROVED  = "approved"
REJECTED  = "rejected"
CANCELLED = "cancelled"
REVOKED   = "revoked"

ALL_STATUSES = {PENDING, APPROVED, REJECTED, CANCELLED, REVOKED}
TERMINAL_STATUSES = {REJECTED, CANCELLED, REVOKED}

# Actor roles in the workflow
REQUESTER = "requester"
APPROVER  = "approver"


class Transition(NamedTuple):
    frm: str
    to: str
    actor_kind: str
    guards: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()


TRANSITIONS: tuple[Transition, ...] = (
    # Applicant cancels their own pending application
    Transition(PENDING,  CANCELLED, REQUESTER),

    # Approver approves or rejects
    Transition(PENDING,  APPROVED,  APPROVER),
    Transition(PENDING,  REJECTED,  APPROVER, guards=("has_reason",)),

    # Requester cancels an approved request (before it begins)
    Transition(APPROVED, CANCELLED, REQUESTER),

    # Approver revokes a previously-approved request
    Transition(APPROVED, REVOKED,   APPROVER, guards=("has_reason",)),
)


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Invalid transition from '{frm}' to '{to}'")
        self.frm = frm
        self.to = to


class ActorNotAllowed(Exception):
    def __init__(self, frm: str, to: str, actor_kind: str):
        super().__init__(f"Actor '{actor_kind}' is not allowed to transition '{frm}' to '{to}'")
        self.frm = frm
        self.to = to
        self.actor_kind = actor_kind


def resolve(frm: str, to: str, actor_kind: str) -> Transition:
    match = [t for t in TRANSITIONS if t.frm == frm and t.to == to]
    if not match:
        raise InvalidTransition(frm, to)
    for t in match:
        if t.actor_kind == actor_kind:
            return t
    raise ActorNotAllowed(frm, to, actor_kind)


def allowed_targets(frm: str, actor_kind: str) -> list[str]:
    return [t.to for t in TRANSITIONS if t.frm == frm and t.actor_kind == actor_kind]
