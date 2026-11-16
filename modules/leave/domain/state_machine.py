"""Authoritative State-Transition Table enforcement for Basis Workflow BW-HR-01.

Governs Leave Direct Approval:
Draft Leave Request -> Pending Current Authority -> Approved — Leave Balance Updated
(zero forwarding loops per basis workflow specification).

Pure Python, tested without Django or DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# States
DRAFT = "draft"
PENDING_CURRENT_AUTHORITY = "pending_current_authority"
APPROVED = "approved"
REJECTED = "rejected"
CANCELLED = "cancelled"

TERMINAL = frozenset({APPROVED, REJECTED, CANCELLED})
IN_FLIGHT = frozenset({DRAFT, PENDING_CURRENT_AUTHORITY})

# Actors
APPLICANT = "applicant"
AUTHORITY = "authority"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot transition leave request from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"Actor {actor_kind!r} is not authorized to move leave request from {frm!r} to {to!r}."
        )
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


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
    # Entry transition (HR-UC-003, BW-HR-01 Step 1):
    # Draft -> Pending Current Authority
    Transition(
        frm=DRAFT,
        to=PENDING_CURRENT_AUTHORITY,
        permission="leave.request.create",
        actors=frozenset({APPLICANT}),
        guards=("has_required_fields", "has_sufficient_balance", "is_supported_type"),
    ),
    # Terminal transition - Direct Approval (HR-UC-004, BW-HR-01 Step 2):
    # Pending Current Authority -> Approved
    Transition(
        frm=PENDING_CURRENT_AUTHORITY,
        to=APPROVED,
        permission="leave.request.approve",
        actors=frozenset({AUTHORITY}),
        guards=("is_assigned_authority", "workflow_order_preserved"),
    ),
    # Terminal transition - Rejection (BW-HR-02 / BR-HR-023):
    Transition(
        frm=PENDING_CURRENT_AUTHORITY,
        to=REJECTED,
        permission="leave.request.approve",
        actors=frozenset({AUTHORITY}),
        guards=("is_assigned_authority",),
    ),
    # Forwarding traversal (BW-HR-03 / CW-HR-01):
    # Pending Current Authority -> Pending Current Authority (next authority assigned)
    Transition(
        frm=PENDING_CURRENT_AUTHORITY,
        to=PENDING_CURRENT_AUTHORITY,
        permission="leave.request.approve",
        actors=frozenset({AUTHORITY}),
        guards=("is_assigned_authority", "has_next_authority"),
    ),
    # Cancellation / Withdrawal by applicant (HR-UC-003 / Phase 6):
    # Pending Current Authority -> Cancelled
    Transition(
        frm=PENDING_CURRENT_AUTHORITY,
        to=CANCELLED,
        permission="leave.request.delete",
        actors=frozenset({APPLICANT}),
        guards=("is_applicant",),
    ),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    """Resolve and validate a state transition against legal moves and actor roles."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    """Return whether a transition edge exists."""
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    """List valid next states from the given state."""
    return sorted(
        t.to for t in TRANSITIONS
        if t.frm == frm and (actor_kind is None or actor_kind in t.actors)
    )
