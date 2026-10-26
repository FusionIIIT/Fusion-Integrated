"""Declarative state machine for Employee Leave Management (ELM).

Defines all legal transitions, permitted actors per edge, terminal states,
and guard conditions based on the finalized ELM Workflow Specifications
(CW-EL-01..04, BW-EL-01..17, BR-EL-014..023).

Pure Python: no database dependencies, executes in milliseconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


# --- Request Status Constants ---
DRAFT = "draft"
SUBMITTED_LEGACY = "submitted"
PENDING_SUBSTITUTE = "pending_substitute"
SUBSTITUTE_DECLINED = "substitute_declined"
PENDING_UNIT_HEAD = "pending_unit_head"
PENDING_SANCTION = "pending_sanction"
AWAITING_DIRECTOR_SANCTION = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
CANCELLATION_PENDING_SANCTION = "cancellation_pending_sanction"
CANCELLED = "cancelled"

# --- Sets for Lifecycle Management ---
TERMINAL_STATES = frozenset({APPROVED, REJECTED, WITHDRAWN, CANCELLED})

IN_FLIGHT_PENDING = frozenset({
    SUBMITTED_LEGACY,
    PENDING_SUBSTITUTE,
    SUBSTITUTE_DECLINED,
    PENDING_UNIT_HEAD,
    PENDING_SANCTION,
    AWAITING_DIRECTOR_SANCTION,
})

ACTIVE_OVERLAP_BLOCKING_STATES = frozenset({
    PENDING_SUBSTITUTE,
    SUBSTITUTE_DECLINED,
    PENDING_UNIT_HEAD,
    PENDING_SANCTION,
    AWAITING_DIRECTOR_SANCTION,
    APPROVED,
    CANCELLATION_PENDING_UNIT_HEAD,
    CANCELLATION_PENDING_SANCTION,
})

# --- Actor Kinds ---
ACTOR_APPLICANT = "applicant"
ACTOR_SUBSTITUTE = "substitute"
ACTOR_UNIT_HEAD = "unit_head"
ACTOR_ESTABLISHMENT = "establishment"
ACTOR_SANCTIONING_AUTHORITY = "sanctioning_authority"
ACTOR_DIRECTOR = "director"
ACTOR_SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str, reason: str = ""):
        msg = f"Cannot transition leave request from {frm!r} to {to!r}."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.frm = frm
        self.to = to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"Actor {actor_kind!r} is not authorized to transition request from {frm!r} to {to!r}."
        )
        self.actor_kind = actor_kind
        self.frm = frm
        self.to = to


class GuardFailed(Exception):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard check {guard!r} failed.")
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    allowed_actors: frozenset[str]
    guards: tuple[str, ...] = ()
    description: str = ""


# --- Authoritative Transition Matrix ---
# Based on CW-EL-01, CW-EL-02, BW-EL-01..11, BR-EL-014..023
TRANSITIONS: tuple[Transition, ...] = (
    # --- New Request Submission (EL-UC-001) ---
    Transition(
        frm=DRAFT,
        to=PENDING_SUBSTITUTE,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        guards=("substitute_required", "substitute_valid", "balance_available", "no_overlap"),
        description="Applicant submits request requiring substitute consent (BW-EL-02, BW-EL-05).",
    ),
    Transition(
        frm=DRAFT,
        to=PENDING_UNIT_HEAD,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        guards=("no_substitute_required", "not_director", "balance_available", "no_overlap"),
        description="Applicant submits request not requiring substitute directly to Unit Head (BW-EL-01, BW-EL-04).",
    ),
    Transition(
        frm=DRAFT,
        to=AWAITING_DIRECTOR_SANCTION,
        allowed_actors=frozenset({ACTOR_DIRECTOR, ACTOR_APPLICANT}),
        guards=("no_substitute_required", "is_director", "balance_available", "no_overlap"),
        description="Director submits request not requiring substitute to self-sanction (BW-EL-07, BR-EL-020).",
    ),

    # --- Substitute Response (EL-UC-002, EL-UC-019) ---
    Transition(
        frm=PENDING_SUBSTITUTE,
        to=PENDING_UNIT_HEAD,
        allowed_actors=frozenset({ACTOR_SUBSTITUTE}),
        guards=("not_director",),
        description="Substitute accepts; consent gate releases to Unit Head (BW-EL-02, BW-EL-05).",
    ),
    Transition(
        frm=PENDING_SUBSTITUTE,
        to=AWAITING_DIRECTOR_SANCTION,
        allowed_actors=frozenset({ACTOR_SUBSTITUTE}),
        guards=("is_director",),
        description="Substitute accepts for Director; consent gate releases to Director self-sanction (BW-EL-08).",
    ),
    Transition(
        frm=PENDING_SUBSTITUTE,
        to=SUBSTITUTE_DECLINED,
        allowed_actors=frozenset({ACTOR_SUBSTITUTE}),
        guards=(),
        description="Substitute declines; request awaits applicant replacement or withdrawal (BW-EL-03, BW-EL-06).",
    ),
    Transition(
        frm=SUBSTITUTE_DECLINED,
        to=PENDING_SUBSTITUTE,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        guards=("substitute_valid",),
        description="Applicant nominates replacement substitute (EL-UC-019, BW-EL-03, BW-EL-06).",
    ),

    # --- Unit Head Review (EL-UC-003, BR-EL-016..018) ---
    Transition(
        frm=PENDING_UNIT_HEAD,
        to=APPROVED,
        allowed_actors=frozenset({ACTOR_UNIT_HEAD}),
        guards=("is_unit_head_final_category", "not_applicant"),
        description="Unit Head gives final approval for CL or RH (BR-EL-016, BW-EL-01..03).",
    ),
    Transition(
        frm=PENDING_UNIT_HEAD,
        to=REJECTED,
        allowed_actors=frozenset({ACTOR_UNIT_HEAD}),
        guards=("is_unit_head_final_category", "not_applicant"),
        description="Unit Head gives final rejection for CL or RH (BR-EL-016, BW-EL-01..03).",
    ),
    Transition(
        frm=PENDING_UNIT_HEAD,
        to=PENDING_SANCTION,
        allowed_actors=frozenset({ACTOR_UNIT_HEAD}),
        guards=("is_higher_sanction_category", "not_applicant"),
        description="Unit Head records recommendation for SCL/EL/COL/VL and routes to Sanctioning Authority (BR-EL-017).",
    ),

    # --- Higher Sanction Review (EL-UC-005, BR-EL-018) ---
    Transition(
        frm=PENDING_SANCTION,
        to=APPROVED,
        allowed_actors=frozenset({ACTOR_SANCTIONING_AUTHORITY}),
        guards=("not_applicant",),
        description="Sanctioning Authority gives final approval for higher-sanction leave (BW-EL-04..06).",
    ),
    Transition(
        frm=PENDING_SANCTION,
        to=REJECTED,
        allowed_actors=frozenset({ACTOR_SANCTIONING_AUTHORITY}),
        guards=("not_applicant",),
        description="Sanctioning Authority gives final rejection for higher-sanction leave (BW-EL-04..06).",
    ),

    # --- Director Self-Sanction (BR-EL-020, BW-EL-07..09) ---
    Transition(
        frm=AWAITING_DIRECTOR_SANCTION,
        to=APPROVED,
        allowed_actors=frozenset({ACTOR_DIRECTOR}),
        guards=("is_director",),
        description="Director self-approves own leave application (BR-EL-020, BW-EL-07..09).",
    ),
    Transition(
        frm=AWAITING_DIRECTOR_SANCTION,
        to=REJECTED,
        allowed_actors=frozenset({ACTOR_DIRECTOR}),
        guards=("is_director",),
        description="Director self-rejects own leave application (BR-EL-020, BW-EL-07..09).",
    ),

    # --- Immediate Withdrawal of In-Flight Request (EL-UC-007, BR-EL-022) ---
    Transition(
        frm=PENDING_SUBSTITUTE,
        to=WITHDRAWN,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        description="Applicant withdraws pending request before approval (BR-EL-022).",
    ),
    Transition(
        frm=SUBSTITUTE_DECLINED,
        to=WITHDRAWN,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        description="Applicant withdraws after substitute decline (BR-EL-022).",
    ),
    Transition(
        frm=PENDING_UNIT_HEAD,
        to=WITHDRAWN,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        description="Applicant withdraws while awaiting Unit Head review (BR-EL-022).",
    ),
    Transition(
        frm=PENDING_SANCTION,
        to=WITHDRAWN,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        description="Applicant withdraws while awaiting higher sanction (BR-EL-022).",
    ),
    Transition(
        frm=AWAITING_DIRECTOR_SANCTION,
        to=WITHDRAWN,
        allowed_actors=frozenset({ACTOR_APPLICANT, ACTOR_DIRECTOR}),
        description="Director withdraws own pending request (BR-EL-022).",
    ),
    Transition(
        frm=SUBMITTED_LEGACY,
        to=WITHDRAWN,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        description="Applicant withdraws legacy submitted request.",
    ),

    # --- Pre-Start Cancellation of Approved Leave (EL-UC-008, CW-EL-02, BR-EL-023) ---
    Transition(
        frm=APPROVED,
        to=CANCELLATION_PENDING_UNIT_HEAD,
        allowed_actors=frozenset({ACTOR_APPLICANT}),
        guards=("before_start_date",),
        description="Applicant requests cancellation of approved leave before start date (BR-EL-023, BW-EL-10..11).",
    ),
    Transition(
        frm=CANCELLATION_PENDING_UNIT_HEAD,
        to=CANCELLED,
        allowed_actors=frozenset({ACTOR_UNIT_HEAD}),
        guards=("is_unit_head_final_category", "not_applicant"),
        description="Unit Head approves cancellation of CL/RH; restores balance (BW-EL-10).",
    ),
    Transition(
        frm=CANCELLATION_PENDING_UNIT_HEAD,
        to=APPROVED,
        allowed_actors=frozenset({ACTOR_UNIT_HEAD}),
        guards=("is_unit_head_final_category", "not_applicant"),
        description="Unit Head rejects cancellation of CL/RH; original approval remains (BW-EL-10).",
    ),
    Transition(
        frm=CANCELLATION_PENDING_UNIT_HEAD,
        to=CANCELLATION_PENDING_SANCTION,
        allowed_actors=frozenset({ACTOR_UNIT_HEAD}),
        guards=("is_higher_sanction_category", "not_applicant"),
        description="Unit Head records recommendation for higher-sanction cancellation (BW-EL-11).",
    ),
    Transition(
        frm=CANCELLATION_PENDING_SANCTION,
        to=CANCELLED,
        allowed_actors=frozenset({ACTOR_SANCTIONING_AUTHORITY}),
        guards=("not_applicant",),
        description="Sanctioning Authority approves cancellation; restores balance (BW-EL-11).",
    ),
    Transition(
        frm=CANCELLATION_PENDING_SANCTION,
        to=APPROVED,
        allowed_actors=frozenset({ACTOR_SANCTIONING_AUTHORITY}),
        guards=("not_applicant",),
        description="Sanctioning Authority rejects cancellation; original approval remains (BW-EL-11).",
    ),
)


# Quick lookup index: (frm, to) -> Transition
_TRANSITION_MAP: dict[tuple[str, str], Transition] = {
    (t.frm, t.to): t for t in TRANSITIONS
}


def is_legal_transition(frm: str, to: str) -> bool:
    """Return True if moving from frm to to is statically defined."""
    return (frm, to) in _TRANSITION_MAP


def get_transition(frm: str, to: str) -> Transition:
    """Return the declared Transition or raise InvalidTransition."""
    if (frm, to) not in _TRANSITION_MAP:
        raise InvalidTransition(frm, to)
    return _TRANSITION_MAP[(frm, to)]


def check_actor(transition: Transition, actor_kind: str) -> None:
    """Raise ActorNotAllowed if actor_kind is not permitted on this edge."""
    if actor_kind not in transition.allowed_actors:
        raise ActorNotAllowed(actor_kind, transition.frm, transition.to)


def allowed_targets_from(frm: str) -> list[str]:
    """List all reachable destination states from frm."""
    return [t.to for t in TRANSITIONS if t.frm == frm]
