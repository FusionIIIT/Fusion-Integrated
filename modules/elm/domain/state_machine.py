"""ELM state-transition tables (Workflow Specifications v1.6).

The STTs in the workflow specification are authoritative; this
module is their executable form. Every row of every Basis Workflow
lands here as a :class:`Transition`, keyed by
``(kind, from_state, actor, guard)``. Services never invent a state
change — they pick the guard that matches the situation and call
:meth:`transition`, which refuses anything not in the table.

Guards are named, not booleans: a guard name says *why* a row
exists, which keeps the table readable next to the specification it
mirrors. Guard evaluation (is the applicant a Director? is
establishment processing configured?) happens in the service layer,
which selects the guard key — the machine only checks that the
selected row exists.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.elm.domain.errors import InvalidTransition
from modules.elm.domain.leave_types import (
    ACTOR_EMPLOYEE,
    ACTOR_ESTABLISHMENT,
    ACTOR_SANCTIONING,
    ACTOR_SUBSTITUTE,
    ACTOR_UNIT_HEAD,
    APPLICANT_ACTION_REQUIRED,
    APPROVED,
    AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_ESTABLISHMENT_ROUTING,
    AWAITING_EXTENSION_SUBSTITUTE,
    AWAITING_EXTENSION_UNIT_HEAD,
    AWAITING_FINAL_SANCTION_DECISION,
    AWAITING_SUBSTITUTE_RESPONSE,
    AWAITING_UNIT_HEAD_REVIEW,
    CANCELLATION_PENDING_ESTABLISHMENT,
    CANCELLATION_PENDING_FINAL,
    CANCELLATION_PENDING_UNIT_HEAD,
    DRAFT,
    EXTENSION_APPLICANT_ACTION_REQUIRED,
    EXTENSION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_FINAL,
    KIND_CANCELLATION,
    KIND_EXTENSION,
    KIND_NEW,
    REJECTED,
    TERMINAL_STATES,
    WITHDRAWN,
)


@dataclass(frozen=True)
class Transition:
    kind: str
    frm: str
    actor: str
    guard: str
    to: str
    task: str | None = None
    """Workflow task completed by taking this transition, if any."""


# -- new leave (BW-EL-01 … BW-EL-05, CW-EL-01) ---------------------------

NEW_LEAVE = (
    # Submission (EL-UC-001). The guard picks the entry state:
    # a substitute-nominated request waits for consent first, a
    # Director's own application goes straight to self-sanction.
    Transition(KIND_NEW, DRAFT, ACTOR_EMPLOYEE,
               "submit_no_substitute_not_director", AWAITING_UNIT_HEAD_REVIEW,
               task="submit"),
    Transition(KIND_NEW, DRAFT, ACTOR_EMPLOYEE,
               "submit_substitute_required", AWAITING_SUBSTITUTE_RESPONSE,
               task="submit"),
    Transition(KIND_NEW, DRAFT, ACTOR_EMPLOYEE,
               "submit_no_substitute_director",
               AWAITING_DIRECTOR_SELF_SANCTION, task="submit"),

    # Substitute consent gate (EL-UC-002, BR-EL-015). Routing does
    # not proceed until required consent is accepted.
    Transition(KIND_NEW, AWAITING_SUBSTITUTE_RESPONSE, ACTOR_SUBSTITUTE,
               "substitute_accepted_not_director", AWAITING_UNIT_HEAD_REVIEW,
               task="substitute_response"),
    Transition(KIND_NEW, AWAITING_SUBSTITUTE_RESPONSE, ACTOR_SUBSTITUTE,
               "substitute_accepted_director",
               AWAITING_DIRECTOR_SELF_SANCTION,
               task="substitute_response"),
    Transition(KIND_NEW, AWAITING_SUBSTITUTE_RESPONSE, ACTOR_SUBSTITUTE,
               "substitute_declined", APPLICANT_ACTION_REQUIRED,
               task="substitute_response"),
    # Recovery after a decline: the applicant may nominate another
    # eligible substitute (BR-EL-014) or withdraw.
    Transition(KIND_NEW, APPLICANT_ACTION_REQUIRED, ACTOR_EMPLOYEE,
               "replacement_nominated", AWAITING_SUBSTITUTE_RESPONSE),

    # Unit Head review (EL-UC-003): final for CL/RH, a
    # recommendation otherwise.
    Transition(KIND_NEW, AWAITING_UNIT_HEAD_REVIEW, ACTOR_UNIT_HEAD,
               "cl_rh_final_approve", APPROVED, task="unit_head_review"),
    Transition(KIND_NEW, AWAITING_UNIT_HEAD_REVIEW, ACTOR_UNIT_HEAD,
               "cl_rh_final_reject", REJECTED, task="unit_head_review"),
    Transition(KIND_NEW, AWAITING_UNIT_HEAD_REVIEW, ACTOR_UNIT_HEAD,
               "higher_recommend_establishment",
               AWAITING_ESTABLISHMENT_ROUTING, task="unit_head_review"),
    Transition(KIND_NEW, AWAITING_UNIT_HEAD_REVIEW, ACTOR_UNIT_HEAD,
               "higher_recommend_no_establishment",
               AWAITING_FINAL_SANCTION_DECISION, task="unit_head_review"),

    # Establishment processing (EL-UC-004): verification and routing,
    # never a sanctioning decision.
    Transition(KIND_NEW, AWAITING_ESTABLISHMENT_ROUTING, ACTOR_ESTABLISHMENT,
               "establishment_routing_valid",
               AWAITING_FINAL_SANCTION_DECISION,
               task="establishment_routing"),

    # Final sanctioning decision (EL-UC-005).
    Transition(KIND_NEW, AWAITING_FINAL_SANCTION_DECISION, ACTOR_SANCTIONING,
               "sanction_approve", APPROVED, task="final_sanction"),
    Transition(KIND_NEW, AWAITING_FINAL_SANCTION_DECISION, ACTOR_SANCTIONING,
               "sanction_reject", REJECTED, task="final_sanction"),

    # Director self-sanction (EL-UC-006, BR-EL-019).
    Transition(KIND_NEW, AWAITING_DIRECTOR_SELF_SANCTION, ACTOR_SANCTIONING,
               "director_self_sanction_approve", APPROVED,
               task="final_sanction"),
    Transition(KIND_NEW, AWAITING_DIRECTOR_SELF_SANCTION, ACTOR_SANCTIONING,
               "director_self_sanction_reject", REJECTED,
               task="final_sanction"),
)

# -- cancellation of approved leave (CW-EL-02) -----------------------------

CANCELLATION = (
    Transition(KIND_CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD,
               ACTOR_UNIT_HEAD, "cl_rh_final_approve", APPROVED,
               task="unit_head_review"),
    Transition(KIND_CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD,
               ACTOR_UNIT_HEAD, "cl_rh_final_reject", REJECTED,
               task="unit_head_review"),
    Transition(KIND_CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD,
               ACTOR_UNIT_HEAD, "higher_recommend_establishment",
               CANCELLATION_PENDING_ESTABLISHMENT,
               task="unit_head_review"),
    Transition(KIND_CANCELLATION, CANCELLATION_PENDING_UNIT_HEAD,
               ACTOR_UNIT_HEAD, "higher_recommend_no_establishment",
               CANCELLATION_PENDING_FINAL, task="unit_head_review"),
    Transition(KIND_CANCELLATION, CANCELLATION_PENDING_ESTABLISHMENT,
               ACTOR_ESTABLISHMENT, "establishment_routing_valid",
               CANCELLATION_PENDING_FINAL, task="establishment_routing"),
    Transition(KIND_CANCELLATION, CANCELLATION_PENDING_FINAL,
               ACTOR_SANCTIONING, "sanction_approve", APPROVED,
               task="final_sanction"),
    Transition(KIND_CANCELLATION, CANCELLATION_PENDING_FINAL,
               ACTOR_SANCTIONING, "sanction_reject", REJECTED,
               task="final_sanction"),
)

# -- extension of ongoing leave (CW-EL-03) ---------------------------------

EXTENSION = (
    # Substitute consent gate, where coverage is required.
    Transition(KIND_EXTENSION, AWAITING_EXTENSION_SUBSTITUTE,
               ACTOR_SUBSTITUTE, "substitute_accepted",
               AWAITING_EXTENSION_UNIT_HEAD, task="substitute_response"),
    Transition(KIND_EXTENSION, AWAITING_EXTENSION_SUBSTITUTE,
               ACTOR_SUBSTITUTE, "substitute_declined",
               EXTENSION_APPLICANT_ACTION_REQUIRED,
               task="substitute_response"),
    Transition(KIND_EXTENSION, EXTENSION_APPLICANT_ACTION_REQUIRED,
               ACTOR_EMPLOYEE, "replacement_nominated",
               AWAITING_EXTENSION_SUBSTITUTE),

    Transition(KIND_EXTENSION, AWAITING_EXTENSION_UNIT_HEAD,
               ACTOR_UNIT_HEAD, "higher_recommend_establishment",
               EXTENSION_PENDING_ESTABLISHMENT,
               task="unit_head_review"),
    Transition(KIND_EXTENSION, AWAITING_EXTENSION_UNIT_HEAD,
               ACTOR_UNIT_HEAD, "higher_recommend_no_establishment",
               EXTENSION_PENDING_FINAL, task="unit_head_review"),
    Transition(KIND_EXTENSION, EXTENSION_PENDING_ESTABLISHMENT,
               ACTOR_ESTABLISHMENT, "establishment_routing_valid",
               EXTENSION_PENDING_FINAL, task="establishment_routing"),
    Transition(KIND_EXTENSION, EXTENSION_PENDING_FINAL,
               ACTOR_SANCTIONING, "sanction_approve", APPROVED,
               task="final_sanction"),
    Transition(KIND_EXTENSION, EXTENSION_PENDING_FINAL,
               ACTOR_SANCTIONING, "sanction_reject", REJECTED,
               task="final_sanction"),
)

# -- cross-cutting withdrawal (BR-EL-022) ----------------------------------
# Valid from every pending, pre-final state of every kind. Taking
# it cancels every remaining task and notifies the concerned roles.

_WITHDRAWABLE = (
    (KIND_NEW, (DRAFT, AWAITING_SUBSTITUTE_RESPONSE,
                APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD_REVIEW,
                AWAITING_DIRECTOR_SELF_SANCTION,
                AWAITING_ESTABLISHMENT_ROUTING,
                AWAITING_FINAL_SANCTION_DECISION)),
    (KIND_CANCELLATION, (CANCELLATION_PENDING_UNIT_HEAD,
                         CANCELLATION_PENDING_ESTABLISHMENT,
                         CANCELLATION_PENDING_FINAL)),
    (KIND_EXTENSION, (AWAITING_EXTENSION_SUBSTITUTE,
                      EXTENSION_APPLICANT_ACTION_REQUIRED,
                      AWAITING_EXTENSION_UNIT_HEAD,
                      EXTENSION_PENDING_ESTABLISHMENT,
                      EXTENSION_PENDING_FINAL)),
)

WITHDRAWALS = tuple(
    Transition(kind, frm, ACTOR_EMPLOYEE, "withdraw_before_final", WITHDRAWN)
    for kind, states in _WITHDRAWABLE for frm in states
)

ALL_TRANSITIONS = NEW_LEAVE + CANCELLATION + EXTENSION + WITHDRAWALS

_INDEX: dict[tuple[str, str, str, str], Transition] = {
    (t.kind, t.frm, t.actor, t.guard): t for t in ALL_TRANSITIONS
}


def transition(kind: str, frm: str, actor: str, guard: str) -> Transition:
    """Look up one transition; raises :class:`InvalidTransition`
    when the combination is not in the table."""
    key = (kind, frm, actor, guard)
    try:
        return _INDEX[key]
    except KeyError:
        raise InvalidTransition(frm) from None


class UnknownTransition(InvalidTransition):
    """The (kind, state, actor, guard) combination has no row."""

    def __init__(self, kind: str, frm: str, actor: str, guard: str):
        super().__init__(frm)
        self.kind = kind
        self.actor = actor
        self.guard = guard


def is_pending(kind: str, state: str) -> bool:
    """A state is pending while it is neither terminal nor withdrawn."""
    return state not in TERMINAL_STATES


def guards_for(kind: str, frm: str, actor: str) -> tuple[str, ...]:
    """Guards that leave ``frm`` under ``actor`` — used by the API
    layer to offer only the actions that are legal right now."""
    return tuple(
        t.guard for t in ALL_TRANSITIONS
        if t.kind == kind and t.frm == frm and t.actor == actor
    )


def initial_state(kind: str, *, substitute_required: bool = False,
                  director_path: bool = False) -> str:
    """The state a request object is born in.

    New applications start as drafts; cancellation and extension
    requests are born already in their first review state (their
    "submission" *is* the review request), with the substitute
    consent gate first when coverage is required.
    """
    if kind == KIND_NEW:
        return DRAFT
    if kind == KIND_CANCELLATION:
        return CANCELLATION_PENDING_UNIT_HEAD
    if substitute_required:
        return AWAITING_EXTENSION_SUBSTITUTE
    return AWAITING_EXTENSION_UNIT_HEAD
