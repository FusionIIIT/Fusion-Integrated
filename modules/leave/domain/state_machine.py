"""The leave request state machine.

A declarative table of legal moves, so an illegal transition is impossible to
express rather than merely rejected, and "who may do this?" has exactly one
answer per edge (the workflow specification's STT, CW-EL-01..04).

Two shapes of request share this table:

    kind = new | extension | cancellation | resumption

A submitted request is never edited in place (BR-EL-034), so a change is a new
row: an extension, a cancellation and a resumption are each a request of their
own linked to the leave they act on. That is what keeps the approved leave
"the base" for an extension, and what makes "cancellation does not edit the
approved leave" structural rather than a convention.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# -- states -------------------------------------------------------------------
DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_FINAL = "awaiting_final"
AWAITING_SELF_SANCTION = "awaiting_self_sanction"
RESUMPTION_PENDING = "resumption_pending"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"
RESUMED = "resumed"

#: Every state a request can be in before a final decision. Withdrawal is
#: available from all of them (CW-EL-01 row 17).
PENDING = frozenset({
    AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL, AWAITING_SELF_SANCTION,
    RESUMPTION_PENDING,
})

#: No further processing is possible.
TERMINAL = frozenset({APPROVED, REJECTED, WITHDRAWN, CANCELLED, RESUMED})

STATES = frozenset({DRAFT} | PENDING | TERMINAL)

# -- request kinds ------------------------------------------------------------
KIND_NEW = "new"
KIND_EXTENSION = "extension"
KIND_CANCELLATION = "cancellation"
KIND_RESUMPTION = "resumption"

#-- actors -------------------------------------------------------------------
# Not designations: lanes, the way placement's state machine reads them. Which
# person occupies a lane for a given request is the routing layer's business.
EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
AUTHORITY = "authority"
SYSTEM = "system"

ACTOR_KINDS = (EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT, AUTHORITY, SYSTEM)


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"A leave request cannot move from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"A {actor_kind} may not move a leave request from {frm!r} to {to!r}.")
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


class GuardFailed(Exception):
    """A guard named in the table is not satisfied. The caller turns this into
    a message written for whoever reads it."""

    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    actor: str
    permission: str
    guards: tuple[str, ...] = field(default_factory=tuple)


def _withdraw_states() -> tuple[Transition, ...]:
    return tuple(
        Transition(s, WITHDRAWN, EMPLOYEE, "leave.application.withdraw",
                   ("not_final",))
        for s in sorted(PENDING)
    )


TRANSITIONS: tuple[Transition, ...] = (
    # -- submission (EL-UC-001) ---------------------------------------------
    # The substitute consent gate comes before any review, including for a
    # Director applicant (CW-EL-01 row 4).
    Transition(DRAFT, AWAITING_SUBSTITUTE, EMPLOYEE, "leave.application.create",
               ("substitute_required",)),
    Transition(DRAFT, AWAITING_UNIT_HEAD, EMPLOYEE, "leave.application.create",
               ("no_substitute_required", "applicant_not_director")),
    Transition(DRAFT, AWAITING_SELF_SANCTION, EMPLOYEE,
               "leave.application.create",
               ("no_substitute_required", "applicant_is_director")),

    # -- the consent gate (EL-UC-002, EL-UC-019) ----------------------------
    Transition(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, SUBSTITUTE,
               "leave.substitute.respond",
               ("consent_accepted", "applicant_not_director")),
    Transition(AWAITING_SUBSTITUTE, AWAITING_SELF_SANCTION, SUBSTITUTE,
               "leave.substitute.respond",
               ("consent_accepted", "applicant_is_director")),
    Transition(AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, SUBSTITUTE,
               "leave.substitute.respond", ("consent_declined",)),
    Transition(APPLICANT_ACTION_REQUIRED, AWAITING_SUBSTITUTE, EMPLOYEE,
               "leave.substitute.nominate", ("replacement_eligible",)),

    # -- Unit Head (EL-UC-003) ----------------------------------------------
    # CL/RH end here: the Unit Head is the final authority (BR-EL-016).
    Transition(AWAITING_UNIT_HEAD, APPROVED, UNIT_HEAD, "leave.request.review",
               ("unit_head_final", "decision_approve")),
    Transition(AWAITING_UNIT_HEAD, REJECTED, UNIT_HEAD, "leave.request.review",
               ("unit_head_final", "decision_reject")),
    # SCL/EL/COL/VL only get a recommendation here, and both outcomes keep
    # going — Not Recommended is not a rejection (BR-EL-017).
    Transition(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, UNIT_HEAD,
               "leave.request.review",
               ("higher_sanction", "establishment_configured")),
    Transition(AWAITING_UNIT_HEAD, AWAITING_FINAL, UNIT_HEAD,
               "leave.request.review", ("higher_sanction",)),

    # -- Establishment processing (EL-UC-004) -------------------------------
    Transition(AWAITING_ESTABLISHMENT, AWAITING_FINAL, ESTABLISHMENT,
               "leave.request.route", ("routing_context_valid",)),

    # -- final sanction (EL-UC-005, BR-EL-020) -------------------------------
    Transition(AWAITING_FINAL, APPROVED, AUTHORITY, "leave.request.approve",
               ("decision_approve",)),
    Transition(AWAITING_FINAL, REJECTED, AUTHORITY, "leave.request.approve",
               ("decision_reject",)),
    # The Director's own leave: one person, two lanes, and the table is the
    # only place that pairing is allowed.
    Transition(AWAITING_SELF_SANCTION, APPROVED, AUTHORITY,
               "leave.request.approve",
               ("applicant_is_director", "decision_approve")),
    Transition(AWAITING_SELF_SANCTION, REJECTED, AUTHORITY,
               "leave.request.approve",
               ("applicant_is_director", "decision_reject")),

    # -- cancellation of approved leave (EL-UC-008, CW-EL-02) ----------------
    # The employee raises it; the decision then follows the same edges as the
    # original leave, so nothing here is new.
    Transition(DRAFT, AWAITING_UNIT_HEAD, EMPLOYEE, "leave.application.cancel",
               ("pre_start",)),

    # -- extension of ongoing leave (EL-UC-009, CW-EL-03) --------------------
    Transition(DRAFT, AWAITING_SUBSTITUTE, EMPLOYEE, "leave.application.extend",
               ("leave_ongoing", "extension_eligible", "substitute_required")),
    Transition(DRAFT, AWAITING_UNIT_HEAD, EMPLOYEE, "leave.application.extend",
               ("leave_ongoing", "extension_eligible", "no_substitute_required")),

    # -- resumption (EL-UC-010, EL-UC-011, CW-EL-04) -------------------------
    Transition(DRAFT, RESUMPTION_PENDING, EMPLOYEE, "leave.resumption.submit",
               ("leave_started", "resumption_eligible")),
    Transition(RESUMPTION_PENDING, RESUMED, AUTHORITY, "leave.resumption.review",
               ()),

    # -- withdrawal, from every pending pre-final state (EL-UC-007) ----------
    *_withdraw_states(),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    """The single lookup every write goes through. `actor_kind` is optional
    only so the table can be introspected; every service call supplies it."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in {t.actor}:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted({t.to for t in TRANSITIONS
                   if t.frm == frm
                   and (actor_kind is None or actor_kind == t.actor)})


def is_pending(status: str) -> bool:
    return status in PENDING


def is_terminal(status: str) -> bool:
    return status in TERMINAL


def outgoing(frm: str) -> tuple[Transition, ...]:
    return tuple(t for t in TRANSITIONS if t.frm == frm)
