"""The application state machine (CW-EL-01, CW-EL-02, CW-EL-03).

A declarative table of legal moves, so an illegal transition is impossible to
express rather than merely rejected, and "who may do this?" has exactly one
answer per edge. Pure Python, so the rules test in milliseconds with no DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- State Constants ---
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
CANCELLATION_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
CANCELLATION_PENDING_FINAL = "cancellation_pending_final"
CANCELLED = "cancelled"

# --- Sets ---
TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED})
PENDING = frozenset({
    AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SELF_SANCTION
})

# --- Actor Constants ---
EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
AUTHORITY = "authority"
DIRECTOR = "director"
SYSTEM = "system"

# --- Category Constants ---
UNIT_HEAD_FINAL = frozenset({"CL", "RH"})
HIGHER_SANCTION = frozenset({"SCL", "EL", "COL", "VL"})

# --- Permission Constants ---
P_CREATE = "leave_management.application.create"
P_RESPOND = "leave_management.application.respond"
P_REVIEW = "leave_management.application.review"
P_DELETE = "leave_management.application.delete"


# --- Exceptions ---
class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move an application from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"A {actor_kind} may not move an application from {frm!r} to {to!r}.")
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


class ScopeMismatch(Exception):
    def __init__(self, category_code: str, scope: str):
        super().__init__(
            f"Category {category_code!r} does not match required scope {scope!r}.")
        self.category_code, self.scope = category_code, scope


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    scope: str = "any"
    guards: tuple[str, ...] = field(default_factory=tuple)


def _make_transition(
    frm: str, to: str, permission: str, actors: frozenset[str],
    scope: str = "any", guards: tuple[str, ...] = ()
) -> Transition:
    """Helper to create a Transition object."""
    return Transition(frm, to, permission, actors, scope, guards)


# --- Transition Definitions ---

TRANSITIONS: tuple[Transition, ...] = (
    # Student/Substitute moves
    _make_transition(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, P_RESPOND,
                      frozenset({SUBSTITUTE}), "any", ("substitute_accepts_non_director",)),
    _make_transition(AWAITING_SUBSTITUTE, AWAITING_DIRECTOR_SELF_SANCTION, P_RESPOND,
                      frozenset({SUBSTITUTE}), "any", ("substitute_accepts_director_applicant",)),
    _make_transition(AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, P_RESPOND,
                      frozenset({SUBSTITUTE}), "any", ("substitute_declines",)),
    _make_transition(APPLICANT_ACTION_REQUIRED, AWAITING_SUBSTITUTE, P_CREATE,
                      frozenset({EMPLOYEE}), "any", ("eligible_replacement_nominated",)),

    # Unit Head Review
    _make_transition(AWAITING_UNIT_HEAD, APPROVED, P_REVIEW,
                      frozenset({UNIT_HEAD}), "unit_head_final", ()),
    _make_transition(AWAITING_UNIT_HEAD, REJECTED, P_REVIEW,
                      frozenset({UNIT_HEAD}), "unit_head_final", ("has_reason",)),
    _make_transition(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, P_REVIEW,
                      frozenset({UNIT_HEAD}), "higher",
                      ("recommendation_recorded", "establishment_configured")),
    _make_transition(AWAITING_UNIT_HEAD, AWAITING_FINAL_SANCTION, P_REVIEW,
                      frozenset({UNIT_HEAD}), "higher",
                      ("recommendation_recorded", "no_establishment_step")),

    # Establishment Review
    _make_transition(AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, P_REVIEW,
                      frozenset({ESTABLISHMENT}), "higher", ("routing_context_valid",)),

    # Final Sanction Review
    _make_transition(AWAITING_FINAL_SANCTION, APPROVED, P_REVIEW,
                      frozenset({AUTHORITY}), "higher", ()),
    _make_transition(AWAITING_FINAL_SANCTION, REJECTED, P_REVIEW,
                      frozenset({AUTHORITY}), "higher", ("has_reason",)),

    # Director Self Sanction
    _make_transition(AWAITING_DIRECTOR_SELF_SANCTION, APPROVED, P_REVIEW,
                      frozenset({DIRECTOR}), "any", ()),
    _make_transition(AWAITING_DIRECTOR_SELF_SANCTION, REJECTED, P_REVIEW,
                      frozenset({DIRECTOR}), "any", ("has_reason",)),

    # Cancellation Flow
    _make_transition(APPROVED, CANCELLATION_PENDING_UNIT_HEAD, P_CREATE,
                      frozenset({EMPLOYEE}), "any", ("before_start_date",)),
    _make_transition(CANCELLATION_PENDING_UNIT_HEAD, CANCELLED, P_REVIEW,
                      frozenset({UNIT_HEAD}), "unit_head_final", ()),
    _make_transition(CANCELLATION_PENDING_UNIT_HEAD, APPROVED, P_REVIEW,
                      frozenset({UNIT_HEAD}), "unit_head_final", ("has_reason",)),
    _make_transition(CANCELLATION_PENDING_UNIT_HEAD, CANCELLATION_PENDING_ESTABLISHMENT, P_REVIEW,
                      frozenset({UNIT_HEAD}), "higher",
                      ("recommendation_recorded", "establishment_configured")),
    _make_transition(CANCELLATION_PENDING_UNIT_HEAD, CANCELLATION_PENDING_FINAL, P_REVIEW,
                      frozenset({UNIT_HEAD}), "higher",
                      ("recommendation_recorded", "no_establishment_step")),
    _make_transition(CANCELLATION_PENDING_ESTABLISHMENT, CANCELLATION_PENDING_FINAL, P_REVIEW,
                      frozenset({ESTABLISHMENT}), "higher", ("routing_context_valid",)),
    _make_transition(CANCELLATION_PENDING_FINAL, CANCELLED, P_REVIEW,
                      frozenset({AUTHORITY}), "higher", ()),
    _make_transition(CANCELLATION_PENDING_FINAL, APPROVED, P_REVIEW,
                      frozenset({AUTHORITY}), "higher", ("has_reason",)),

    # Withdrawal (Generator expression)
    *(
        _make_transition(s, WITHDRAWN, P_DELETE, frozenset({EMPLOYEE}), "any")
        for s in PENDING
    )
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(
    frm: str, to: str, actor_kind: str | None = None, category_code: str | None = None
) -> Transition:
    """The single lookup every write goes through."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)

    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)

    if category_code is not None:
        if t.scope == "unit_head_final" and category_code not in UNIT_HEAD_FINAL:
            raise ScopeMismatch(category_code, "unit_head_final")
        if t.scope == "higher" and category_code not in HIGHER_SANCTION:
            raise ScopeMismatch(category_code, "higher")

    return t


def is_legal(frm: str, to: str) -> bool:
    """Checks if a transition is defined in the state machine."""
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    """Returns a sorted list of states reachable from frm by actor_kind."""
    return sorted(t.to for t in TRANSITIONS
                  if t.frm == frm
                  and (actor_kind is None or actor_kind in t.actors))


def initial_state(substitute_required: bool, applicant_is_director: bool) -> str:
    """Determines the initial state based on application requirements."""
    if substitute_required:
        return AWAITING_SUBSTITUTE
    if applicant_is_director:
        return AWAITING_DIRECTOR_SELF_SANCTION
    return AWAITING_UNIT_HEAD
