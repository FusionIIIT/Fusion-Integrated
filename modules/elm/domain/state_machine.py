"""ELM leave-request state machine (CW-EL-01 through CW-EL-04).

A declarative table of legal moves mirroring the placement module pattern.
Every write path resolves through ``resolve()``, so an illegal transition is
impossible to express rather than merely rejected. Pure Python -- tests run
in milliseconds without the database.

States and transitions are derived from the synchronized specification:
- CW-EL-01: New leave application workflow
- CW-EL-02: Cancellation of approved leave workflow
- CW-EL-03: Extension of ongoing leave workflow
- CW-EL-04: Resumption / duty-resume workflow
"""
from __future__ import annotations

from dataclasses import dataclass, field


# -- States -------------------------------------------------------------------

# New-request lifecycle (CW-EL-01)
DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_SANCTION = "awaiting_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

# Ongoing leave
ONGOING = "ongoing"

# Cancellation sub-lifecycle (CW-EL-02)
CANCEL_REQUESTED = "cancel_requested"
CANCELLED = "cancelled"

# Extension sub-lifecycle (CW-EL-03)
EXTENSION_REQUESTED = "extension_requested"
EXTENSION_APPROVED = "extension_approved"

# Resumption sub-lifecycle (CW-EL-04)
RESUMPTION_SUBMITTED = "resumption_submitted"
RESUMPTION_REVIEWED = "resumption_reviewed"

TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED})
IN_FLIGHT = frozenset({
    DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_SANCTION,
})


# -- Actor kinds --------------------------------------------------------------

EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"     # Deputy Registrar (Estt.)
SANCTION_AUTH = "sanction_authority" # Dean / Registrar / Director
DIRECTOR = "director"               # self-sanction special case
SYSTEM = "system"                   # SLA escalation, year-end


# -- Exceptions ---------------------------------------------------------------

class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move a leave request from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"A {actor_kind} may not move a leave request from {frm!r} to {to!r}.")
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


class GuardFailed(Exception):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


# -- Transition definition ----------------------------------------------------

@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


# -- Transition table ----------------------------------------------------------
# Mirrors the four composite workflows CW-EL-01 through CW-EL-04.

TRANSITIONS: tuple[Transition, ...] = (

    # === CW-EL-01: New leave application ===================================

    # Employee submits a new request (BR-EL-001, BR-EL-034).
    Transition(DRAFT, AWAITING_SUBSTITUTE, "elm.leave.apply",
               frozenset({EMPLOYEE}),
               ("category_eligible", "balance_sufficient", "no_overlap",
                "substitute_required")),

    # Submit without substitute (CL/RH go straight to Unit Head).
    Transition(DRAFT, AWAITING_UNIT_HEAD, "elm.leave.apply",
               frozenset({EMPLOYEE}),
               ("category_eligible", "balance_sufficient", "no_overlap",
                "no_substitute_required")),

    # Substitute accepts -> advance (BR-EL-015).
    Transition(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, "elm.leave.apply",
               frozenset({SUBSTITUTE}),
               ("substitute_accepted",)),

    # Substitute declines -> back to draft for re-nomination (BR-EL-015).
    Transition(AWAITING_SUBSTITUTE, DRAFT, "elm.leave.apply",
               frozenset({SUBSTITUTE}),
               ("substitute_declined",)),

    # Unit Head sanctions CL/RH directly (BR-EL-016).
    Transition(AWAITING_UNIT_HEAD, APPROVED, "elm.leave.approve",
               frozenset({UNIT_HEAD}),
               ("cl_or_rh",)),

    # Unit Head recommends / not-recommends for higher sanction (BR-EL-017).
    Transition(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, "elm.leave.approve",
               frozenset({UNIT_HEAD}),
               ("higher_sanction", "establishment_configured")),

    Transition(AWAITING_UNIT_HEAD, AWAITING_SANCTION, "elm.leave.approve",
               frozenset({UNIT_HEAD}),
               ("higher_sanction", "no_establishment")),

    # Optional Establishment step (BR-EL-019).
    Transition(AWAITING_ESTABLISHMENT, AWAITING_SANCTION, "elm.leave.approve",
               frozenset({ESTABLISHMENT})),

    # Final Sanctioning Authority approves or rejects (BR-EL-018).
    Transition(AWAITING_SANCTION, APPROVED, "elm.leave.approve",
               frozenset({SANCTION_AUTH})),

    Transition(AWAITING_SANCTION, REJECTED, "elm.leave.approve",
               frozenset({SANCTION_AUTH}),
               ("has_reason",)),

    # Unit Head rejects CL/RH (BR-EL-016).
    Transition(AWAITING_UNIT_HEAD, REJECTED, "elm.leave.approve",
               frozenset({UNIT_HEAD}),
               ("has_reason",)),

    # Director self-sanction (BR-EL-020).
    Transition(DRAFT, APPROVED, "elm.leave.approve",
               frozenset({DIRECTOR}),
               ("category_eligible", "balance_sufficient", "no_overlap",
                "is_director_self")),

    # Withdrawal by employee at any pre-approval stage (BR-EL-022).
    *(Transition(s, WITHDRAWN, "elm.leave.cancel",
                 frozenset({EMPLOYEE}))
      for s in (DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD,
                AWAITING_ESTABLISHMENT, AWAITING_SANCTION)),

    # Approved -> Ongoing (system marks when leave start date arrives).
    Transition(APPROVED, ONGOING, "elm.leave.modify",
               frozenset({SYSTEM}),
               ("start_date_reached",)),

    # === CW-EL-02: Cancellation of approved leave before start =============

    Transition(APPROVED, CANCEL_REQUESTED, "elm.leave.cancel",
               frozenset({EMPLOYEE}),
               ("before_start_date",)),

    # Cancellation uses same hierarchy (BR-EL-023).
    Transition(CANCEL_REQUESTED, CANCELLED, "elm.leave.approve",
               frozenset({UNIT_HEAD, SANCTION_AUTH})),

    # Cancellation rejected -> leave stays approved.
    Transition(CANCEL_REQUESTED, APPROVED, "elm.leave.approve",
               frozenset({UNIT_HEAD, SANCTION_AUTH}),
               ("has_reason",)),

    # === CW-EL-03: Extension of ongoing EL/COL/VL ==========================

    Transition(ONGOING, EXTENSION_REQUESTED, "elm.leave.modify",
               frozenset({EMPLOYEE}),
               ("extendable_category", "balance_sufficient")),

    # Extension goes through substitute gate -> Unit Head -> sanction.
    Transition(EXTENSION_REQUESTED, EXTENSION_APPROVED, "elm.leave.approve",
               frozenset({SANCTION_AUTH, UNIT_HEAD}),
               ("extension_validated",)),

    Transition(EXTENSION_REQUESTED, ONGOING, "elm.leave.approve",
               frozenset({SANCTION_AUTH, UNIT_HEAD}),
               ("has_reason",)),

    # === CW-EL-04: Resumption / early return ================================

    Transition(ONGOING, RESUMPTION_SUBMITTED, "elm.leave.modify",
               frozenset({EMPLOYEE}),
               ("resumable_category",)),

    # Sanctioning authority reviews resumption (BR-EL-027).
    Transition(RESUMPTION_SUBMITTED, RESUMPTION_REVIEWED, "elm.leave.approve",
               frozenset({SANCTION_AUTH}),
               ("resumption_verified",)),
)

_INDEX: dict[tuple[str, str], Transition] = {}
for _t in TRANSITIONS:
    _INDEX.setdefault((_t.frm, _t.to), _t)


# -- Public API ----------------------------------------------------------------

def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    """The single lookup every write goes through."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted({t.to for t in TRANSITIONS
                   if t.frm == frm
                   and (actor_kind is None or actor_kind in t.actors)})
