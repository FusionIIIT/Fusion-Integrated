"""The leave request state machine (CW-EL-01, CW-EL-02, CW-EL-03, CW-EL-04).

A declarative table of (state, event) -> state, so an illegal move is
impossible to express rather than merely rejected, and "who may do this?"
has exactly one answer per edge. Pure Python, so it tests with no database.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

CANCELLATION_AWAITING_UNIT_HEAD = "cancellation_awaiting_unit_head"
CANCELLATION_AWAITING_ESTABLISHMENT = "cancellation_awaiting_establishment"
CANCELLATION_AWAITING_FINAL = "cancellation_awaiting_final_sanction"
CANCELLED = "cancelled"

EXTENSION_AWAITING_SUBSTITUTE = "extension_awaiting_substitute"
EXTENSION_APPLICANT_ACTION_REQUIRED = "extension_applicant_action_required"
EXTENSION_AWAITING_UNIT_HEAD = "extension_awaiting_unit_head"
EXTENSION_AWAITING_ESTABLISHMENT = "extension_awaiting_establishment"
EXTENSION_AWAITING_FINAL = "extension_awaiting_final_sanction"

RESUMPTION_REVIEW_PENDING = "resumption_review_pending"
RESUMPTION_NO_ADJUSTMENT = "resumption_reviewed_no_adjustment"
RESUMPTION_EARLY = "resumption_reviewed_early_return"
RESUMPTION_LATE = "resumption_reviewed_late_return"

STATUSES: tuple[str, ...] = (
    DRAFT, AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION,
    AWAITING_DIRECTOR_SELF_SANCTION, APPROVED, REJECTED, WITHDRAWN,
    CANCELLATION_AWAITING_UNIT_HEAD, CANCELLATION_AWAITING_ESTABLISHMENT,
    CANCELLATION_AWAITING_FINAL, CANCELLED,
    EXTENSION_AWAITING_SUBSTITUTE, EXTENSION_APPLICANT_ACTION_REQUIRED,
    EXTENSION_AWAITING_UNIT_HEAD, EXTENSION_AWAITING_ESTABLISHMENT,
    EXTENSION_AWAITING_FINAL,
    RESUMPTION_REVIEW_PENDING, RESUMPTION_NO_ADJUSTMENT, RESUMPTION_EARLY,
    RESUMPTION_LATE,
)

#: Withdrawable while the request is still pending, never after final approval.
PENDING = frozenset({
    DRAFT, AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION,
    AWAITING_DIRECTOR_SELF_SANCTION, CANCELLATION_AWAITING_UNIT_HEAD,
    CANCELLATION_AWAITING_ESTABLISHMENT, CANCELLATION_AWAITING_FINAL,
    EXTENSION_AWAITING_SUBSTITUTE, EXTENSION_APPLICANT_ACTION_REQUIRED,
    EXTENSION_AWAITING_UNIT_HEAD, EXTENSION_AWAITING_ESTABLISHMENT,
    EXTENSION_AWAITING_FINAL,
})

#: Nothing more can happen to these.
TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED, RESUMPTION_NO_ADJUSTMENT,
                      RESUMPTION_EARLY, RESUMPTION_LATE})

DECIDED = frozenset({APPROVED}) | TERMINAL

# Events.
SUBMIT = "submit"
ACCEPT = "accept"
DECLINE = "decline"
REPLACE = "replace_substitute"
RECOMMEND = "recommend"
APPROVE = "approve"
REJECT = "reject"
FORWARD = "forward"
WITHDRAW = "withdraw"
REQUEST_CANCELLATION = "request_cancellation"
REQUEST_EXTENSION = "request_extension"
SUBMIT_RESUMPTION = "submit_resumption"
REVIEW_NORMAL = "review_normal"
REVIEW_EARLY = "review_early"
REVIEW_LATE = "review_late"

EVENTS: tuple[str, ...] = (SUBMIT, ACCEPT, DECLINE, REPLACE, RECOMMEND, APPROVE,
                           REJECT, FORWARD, WITHDRAW, REQUEST_CANCELLATION,
                           REQUEST_EXTENSION, SUBMIT_RESUMPTION, REVIEW_NORMAL,
                           REVIEW_EARLY, REVIEW_LATE)

# Actor kinds. EMPLOYEE covers faculty and staff; the Director is separate only
# because their own leave takes a different route.
EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTIONING_AUTHORITY = "sanctioning_authority"
DIRECTOR = "director"
ADMIN = "admin"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, event: str):
        super().__init__(f"There is no {event!r} action on a {frm!r} request.")
        self.frm, self.event = frm, event


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, event: str):
        super().__init__(
            f"A {actor_kind} may not perform {event!r} on a {frm!r} request.")
        self.actor_kind, self.frm, self.event = actor_kind, frm, event


@dataclass(frozen=True)
class Transition:
    frm: str
    event: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)
    #: Which workflow this edge belongs to, for tracing a report line back.
    workflow: str = "CW-EL-01"


def _employee(frm: str, event: str, to: str, permission: str,
              *guards: str, workflow: str = "CW-EL-01") -> Transition:
    return Transition(frm, event, to, permission, frozenset({EMPLOYEE}), guards,
                      workflow)


def _review(frm: str, event: str, to: str, *guards: str,
            workflow: str = "CW-EL-01", authority: bool = False) -> Transition:
    """A decision recorded by the officer the resolved path points at."""
    kind = SANCTIONING_AUTHORITY if authority else UNIT_HEAD
    permission = "leave.request.approve" if authority else "leave.request.review"
    return Transition(frm, event, to, permission, frozenset({kind, DIRECTOR}),
                      guards, workflow)


def _establishment(frm: str, to: str, *guards: str,
                   workflow: str = "CW-EL-01") -> Transition:
    return Transition(frm, FORWARD, to, "leave.request.review",
                      frozenset({ESTABLISHMENT}), guards, workflow)


def _resumption(frm: str, event: str, to: str, *guards: str) -> Transition:
    """BR-EL-027: the applicable Sanctioning Authority reviews a resumption."""
    return Transition(frm, event, to, "leave.resumption.review",
                      frozenset({SANCTIONING_AUTHORITY, DIRECTOR}), guards,
                      "CW-EL-04")


#: Every legal edge. CW-EL-01 (new leave), CW-EL-02 (cancellation),
#: CW-EL-03 (extension) and CW-EL-04 (resumption) are all here, one table.
TRANSITIONS: tuple[Transition, ...] = (
    # -- EL-UC-001: submission picks the route -----------------------------
    _employee(DRAFT, SUBMIT, AWAITING_SUBSTITUTE, "leave.request.create",
              "request_valid", "substitute_required", "substitute_nominated",
              "applicant_not_director"),
    _employee(DRAFT, SUBMIT, AWAITING_UNIT_HEAD, "leave.request.create",
              "request_valid", "no_substitute_required", "applicant_not_director"),
    _employee(DRAFT, SUBMIT, AWAITING_DIRECTOR_SELF_SANCTION,
              "leave.request.create", "request_valid", "applicant_is_director"),

    # -- EL-UC-002 and EL-UC-019: the consent gate and its recovery ---------
    Transition(AWAITING_SUBSTITUTE, ACCEPT, AWAITING_UNIT_HEAD,
               "leave.substitute.review", frozenset({SUBSTITUTE}),
               ("substitute_accepted", "applicant_not_director")),
    Transition(AWAITING_SUBSTITUTE, ACCEPT, AWAITING_DIRECTOR_SELF_SANCTION,
               "leave.substitute.review", frozenset({SUBSTITUTE}),
               ("substitute_accepted", "applicant_is_director")),
    Transition(AWAITING_SUBSTITUTE, DECLINE, APPLICANT_ACTION_REQUIRED,
               "leave.substitute.review", frozenset({SUBSTITUTE}),
               ("substitute_declined",)),
    _employee(APPLICANT_ACTION_REQUIRED, REPLACE, AWAITING_SUBSTITUTE,
              "leave.request.create", "replacement_eligible",
              "substitute_nominated"),

    # -- EL-UC-003: CL/RH ends at the Unit Head (BR-EL-016) ----------------
    _review(AWAITING_UNIT_HEAD, APPROVE, APPROVED,
            "unit_head_final_category", "not_own_request"),
    _review(AWAITING_UNIT_HEAD, REJECT, REJECTED,
            "unit_head_final_category", "has_reason", "not_own_request"),

    # -- EL-UC-003 to EL-UC-005: the higher-sanction path (BR-EL-017..019) --
    _review(AWAITING_UNIT_HEAD, RECOMMEND, AWAITING_ESTABLISHMENT,
            "higher_sanction", "establishment_configured", "not_own_request"),
    _review(AWAITING_UNIT_HEAD, RECOMMEND, AWAITING_FINAL_SANCTION,
            "higher_sanction", "no_establishment_step", "not_own_request"),
    _establishment(AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION,
                   "routing_context_valid", "not_own_request"),
    _review(AWAITING_FINAL_SANCTION, APPROVE, APPROVED,
            "higher_sanction", "not_own_request", authority=True),
    _review(AWAITING_FINAL_SANCTION, REJECT, REJECTED,
            "higher_sanction", "has_reason", "not_own_request", authority=True),

    # -- BR-EL-020: the Director's own leave ---------------------------------
    # The Director self-sanction path still uses not_own_request because
    # actor_kind resolves the Director applicant to DIRECTOR, but the guard
    # ensures the authority role (also the Director) cannot approve their own
    # request through a different actor identity.
    _review(AWAITING_DIRECTOR_SELF_SANCTION, APPROVE, APPROVED,
            "applicant_is_director", "not_own_request", workflow="CW-EL-01",
            authority=True),
    _review(AWAITING_DIRECTOR_SELF_SANCTION, REJECT, REJECTED,
            "applicant_is_director", "has_reason", "not_own_request",
            workflow="CW-EL-01", authority=True),

    # -- EL-UC-008 and CW-EL-02: cancellation of an approved leave ----------
    _employee(DRAFT, REQUEST_CANCELLATION, CANCELLATION_AWAITING_UNIT_HEAD,
              "leave.cancellation.create", "parent_approved", "not_started",
              workflow="CW-EL-02"),
    _review(CANCELLATION_AWAITING_UNIT_HEAD, APPROVE, CANCELLED,
            "original_unit_head_final", "not_own_request", workflow="CW-EL-02"),
    _review(CANCELLATION_AWAITING_UNIT_HEAD, REJECT, APPROVED,
            "original_unit_head_final", "has_reason", "not_own_request",
            workflow="CW-EL-02"),
    _review(CANCELLATION_AWAITING_UNIT_HEAD, RECOMMEND,
            CANCELLATION_AWAITING_ESTABLISHMENT, "higher_sanction",
            "establishment_configured", "not_own_request", workflow="CW-EL-02"),
    _review(CANCELLATION_AWAITING_UNIT_HEAD, RECOMMEND,
            CANCELLATION_AWAITING_FINAL, "higher_sanction",
            "no_establishment_step", "not_own_request", workflow="CW-EL-02"),
    _establishment(CANCELLATION_AWAITING_ESTABLISHMENT,
                   CANCELLATION_AWAITING_FINAL, "routing_context_valid",
                   "not_own_request", workflow="CW-EL-02"),
    _review(CANCELLATION_AWAITING_FINAL, APPROVE, CANCELLED, "higher_sanction",
            "not_own_request", workflow="CW-EL-02", authority=True),
    _review(CANCELLATION_AWAITING_FINAL, REJECT, APPROVED, "higher_sanction",
            "has_reason", "not_own_request", workflow="CW-EL-02", authority=True),

    # -- EL-UC-009 and CW-EL-03: extending an ongoing EL/COL/VL -------------
    _employee(DRAFT, REQUEST_EXTENSION, EXTENSION_AWAITING_SUBSTITUTE,
              "leave.extension.create", "parent_ongoing_extendable",
              "request_valid", "substitute_required", "substitute_nominated",
              workflow="CW-EL-03"),
    _employee(DRAFT, REQUEST_EXTENSION, EXTENSION_AWAITING_UNIT_HEAD,
              "leave.extension.create", "parent_ongoing_extendable",
              "request_valid", "no_substitute_required", workflow="CW-EL-03"),
    Transition(EXTENSION_AWAITING_SUBSTITUTE, ACCEPT,
               EXTENSION_AWAITING_UNIT_HEAD, "leave.substitute.review",
               frozenset({SUBSTITUTE}), ("substitute_accepted",),
               workflow="CW-EL-03"),
    Transition(EXTENSION_AWAITING_SUBSTITUTE, DECLINE,
               EXTENSION_APPLICANT_ACTION_REQUIRED, "leave.substitute.review",
               frozenset({SUBSTITUTE}), ("substitute_declined",),
               workflow="CW-EL-03"),
    _employee(EXTENSION_APPLICANT_ACTION_REQUIRED, REPLACE,
              EXTENSION_AWAITING_SUBSTITUTE, "leave.request.create",
              "replacement_eligible", "substitute_nominated", workflow="CW-EL-03"),
    _review(EXTENSION_AWAITING_UNIT_HEAD, RECOMMEND,
            EXTENSION_AWAITING_ESTABLISHMENT, "higher_sanction",
            "establishment_configured", "not_own_request", workflow="CW-EL-03"),
    _review(EXTENSION_AWAITING_UNIT_HEAD, RECOMMEND, EXTENSION_AWAITING_FINAL,
            "higher_sanction", "no_establishment_step", "not_own_request",
            workflow="CW-EL-03"),
    _establishment(EXTENSION_AWAITING_ESTABLISHMENT, EXTENSION_AWAITING_FINAL,
                   "routing_context_valid", "not_own_request", workflow="CW-EL-03"),
    _review(EXTENSION_AWAITING_FINAL, APPROVE, APPROVED, "higher_sanction",
            "not_own_request", workflow="CW-EL-03", authority=True),
    # A refused extension leaves the original approved leave exactly as it was.
    _review(EXTENSION_AWAITING_FINAL, REJECT, APPROVED, "higher_sanction",
            "has_reason", "not_own_request", workflow="CW-EL-03", authority=True),

    # -- EL-UC-010 and EL-UC-011: resumption, with no generic closed state ---
    _employee(APPROVED, SUBMIT_RESUMPTION, RESUMPTION_REVIEW_PENDING,
              "leave.resumption.create", "resumption_reviewed_category",
              workflow="CW-EL-04"),
    _resumption(RESUMPTION_REVIEW_PENDING, REVIEW_NORMAL,
                RESUMPTION_NO_ADJUSTMENT, "resumption_dates_match",
                "not_own_request"),
    _resumption(RESUMPTION_REVIEW_PENDING, REVIEW_EARLY, RESUMPTION_EARLY,
                "resumption_early", "not_own_request"),
    _resumption(RESUMPTION_REVIEW_PENDING, REVIEW_LATE, RESUMPTION_LATE,
                "resumption_late", "not_own_request"),

    # -- BR-EL-022: withdrawal, immediate and available until the decision --
    *(_employee(state, WITHDRAW, WITHDRAWN, "leave.request.delete",
                "not_finally_approved")
      for state in sorted(PENDING - {DRAFT})),
    _employee(DRAFT, WITHDRAW, WITHDRAWN, "leave.request.delete"),
)

_INDEX = {(t.frm, t.event): t for t in TRANSITIONS}


def resolve(frm: str, event: str, actor_kind: str | None = None) -> Transition:
    """The single lookup every write path goes through."""
    t = _INDEX.get((frm, event))
    if t is None:
        raise InvalidTransition(frm, event)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, event)
    return t


def is_legal(frm: str, event: str) -> bool:
    return (frm, event) in _INDEX


def is_pending(state: str) -> bool:
    return state in PENDING


def is_terminal(state: str) -> bool:
    return state in TERMINAL


def allowed_events(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted(t.event for t in TRANSITIONS
                  if t.frm == frm
                  and (actor_kind is None or actor_kind in t.actors))


def permission_codes() -> frozenset[str]:
    return frozenset(t.permission for t in TRANSITIONS)


def resumption_event(*, actual: date, approved_end: date) -> str:
    """BR-EL-028: normal, early and late are three reviewable outcomes."""
    if actual == approved_end:
        return REVIEW_NORMAL
    if actual < approved_end:
        return REVIEW_EARLY
    return REVIEW_LATE
