"""The leave-request state machine (CW-EL-01…04, the authoritative STTs).

Pure Python, no Django. The STT in the workflow specification is the source:
every status below appears there, and every transition carries the actor kind
and the permission code a service must enforce. Guards are string names so
this module never has to know what a balance or a calendar is.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# -- statuses (workflow state names, snake_cased) --------------------------
AWAITING_SUBSTITUTE = "awaiting_substitute_response"
APPLICANT_ACTION = "applicant_action_required"
AWAITING_UH_REVIEW = "awaiting_unit_head_review"
AWAITING_ESTABLISHMENT = "awaiting_establishment_routing"
AWAITING_FINAL = "awaiting_final_sanction_decision"
AWAITING_DIRECTOR = "awaiting_director_self_sanction"

APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLED = "cancelled"          # a base request after its cancellation is approved

STATUS_CHOICES: list[tuple[str, str]] = [
    (AWAITING_SUBSTITUTE, "Awaiting substitute response"),
    (APPLICANT_ACTION, "Applicant action required"),
    (AWAITING_UH_REVIEW, "Awaiting Unit Head review"),
    (AWAITING_ESTABLISHMENT, "Awaiting establishment routing"),
    (AWAITING_FINAL, "Awaiting final sanction decision"),
    (AWAITING_DIRECTOR, "Awaiting Director self-sanction"),
    (APPROVED, "Approved"),
    (REJECTED, "Rejected"),
    (WITHDRAWN, "Withdrawn"),
    (CANCELLED, "Cancelled"),
]

#: Still in flight: withdrawal is available, tasks are actionable, SLA
#: thresholds apply (BR-EL-022, BR-EL-032/033).
PENDING: frozenset[str] = frozenset({
    AWAITING_SUBSTITUTE, APPLICANT_ACTION, AWAITING_UH_REVIEW,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL, AWAITING_DIRECTOR,
})

TERMINAL: frozenset[str] = frozenset({APPROVED, REJECTED, WITHDRAWN, CANCELLED})

# -- actor kinds -----------------------------------------------------------
EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
AUTHORITY = "authority"
SYSTEM = "system"

# -- outbound transitions ---------------------------------------------------
# Withdrawal (EL-UC-007) is cross-cutting across every pending state and is
# declared once below rather than repeated per state.


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move a leave request from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(InvalidTransition):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(frm, to)
        self.actor_kind = actor_kind
        self.args = (f"A {actor_kind} cannot move a leave request from "
                     f"{frm!r} to {to!r}.")


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    actor: str
    permission: str
    #: Substitute consent gate (BR-EL-015): routing cannot continue until the
    #: nominated substitute accepts. Decline parks the request with the
    #: applicant (EL-UC-019 / EL-UC-007 recovery).
    guards: tuple[str, ...] = field(default_factory=tuple)


_TRANSITIONS: tuple[Transition, ...] = (
    # EL-UC-002 — substitute responds.
    Transition(AWAITING_SUBSTITUTE, AWAITING_UH_REVIEW, SUBSTITUTE,
               "leave.substitute.respond", ("substitute_accepted",)),
    Transition(AWAITING_SUBSTITUTE, AWAITING_DIRECTOR, SUBSTITUTE,
               "leave.substitute.respond", ("substitute_accepted",
                                            "applicant_is_director")),
    # Self-approval guard: when the applicant *is* their unit's head, the
    # file skips their own desk and enters at establishment after consent.
    Transition(AWAITING_SUBSTITUTE, AWAITING_ESTABLISHMENT, SUBSTITUTE,
               "leave.substitute.respond", ("substitute_accepted",
                                            "applicant_is_unit_head")),
    Transition(AWAITING_SUBSTITUTE, APPLICANT_ACTION, SUBSTITUTE,
               "leave.substitute.respond", ("substitute_declined",)),

    # EL-UC-019 — applicant replaces a declined substitute.
    Transition(APPLICANT_ACTION, AWAITING_SUBSTITUTE, EMPLOYEE,
               "leave.request.create", ("replacement_nominated",)),

    # EL-UC-003 — Unit Head review.
    # CL/RH (and their cancellations) are Unit-Head-final (BR-EL-016).
    Transition(AWAITING_UH_REVIEW, APPROVED, UNIT_HEAD,
               "leave.request.approve", ("unit_head_final", "outcome_approve")),
    Transition(AWAITING_UH_REVIEW, REJECTED, UNIT_HEAD,
               "leave.request.approve", ("unit_head_final", "outcome_reject")),
    # Higher-sanction (SCL/EL/COL/VL, extensions, higher cancellations): both
    # recommendation outcomes continue; Not Recommended is NOT final
    # (BR-EL-017).
    Transition(AWAITING_UH_REVIEW, AWAITING_ESTABLISHMENT, UNIT_HEAD,
               "leave.request.approve", ("higher_sanction",
                                         "establishment_configured")),
    Transition(AWAITING_UH_REVIEW, AWAITING_FINAL, UNIT_HEAD,
               "leave.request.approve", ("higher_sanction",
                                         "no_establishment_step")),

    # EL-UC-004 — Establishment verifies and forwards (BR-EL-019).
    Transition(AWAITING_ESTABLISHMENT, AWAITING_FINAL, ESTABLISHMENT,
               "leave.request.route", ()),

    # EL-UC-005 — final sanction, including Director self-sanction (BR-EL-020).
    Transition(AWAITING_FINAL, APPROVED, AUTHORITY,
               "leave.request.sanction", ("outcome_approve",)),
    Transition(AWAITING_FINAL, REJECTED, AUTHORITY,
               "leave.request.sanction", ("outcome_reject",)),
    Transition(AWAITING_DIRECTOR, APPROVED, AUTHORITY,
               "leave.request.sanction", ("applicant_is_director",
                                          "outcome_approve")),
    Transition(AWAITING_DIRECTOR, REJECTED, AUTHORITY,
               "leave.request.sanction", ("applicant_is_director",
                                          "outcome_reject")),
)

#: Withdrawal from every pending pre-final state (BR-EL-022, CFR-EL-018).
#: Immediate: no approval of the withdrawal itself is required.
WITHDRAWABLE: frozenset[str] = PENDING

_INDEX: dict[tuple[str, str], list[Transition]] = {}
for _t in _TRANSITIONS:
    _INDEX.setdefault((_t.frm, _t.to), []).append(_t)


def candidates(frm: str, to: str) -> list[Transition]:
    return list(_INDEX.get((frm, to), ()))


def resolve(frm: str, to: str, actor_kind: str) -> Transition:
    """The one transition matching this move and actor, or an exception.

    Withdrawal is resolved by the service (its permission is the applicant's
    own `leave.request.delete`), so it is not in this table.
    """
    for t in candidates(frm, to):
        if t.actor == actor_kind:
            return t
    if candidates(frm, to):
        raise ActorNotAllowed(actor_kind, frm, to)
    raise InvalidTransition(frm, to)


def is_legal(frm: str, to: str, actor_kind: str | None = None) -> bool:
    opts = candidates(frm, to)
    if actor_kind is None:
        return bool(opts)
    return any(t.actor == actor_kind for t in opts)


def allowed_targets(frm: str, actor_kind: str) -> list[str]:
    return sorted({t.to for t in _TRANSITIONS
                   if t.frm == frm and t.actor == actor_kind})
