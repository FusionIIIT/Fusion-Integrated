"""Declarative leave lifecycle (WF-EL-01..05).

An illegal transition is inexpressible: resolve() only returns rows that exist
in TRANSITIONS.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from modules.leave.domain.categories import HIGHER_SANCTION, UNIT_HEAD_FINAL

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
AWAITING_DIRECTOR_SELF = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLATION_PENDING = "cancellation_pending"
CANCELLED = "cancelled"
AWAITING_RESUMPTION = "awaiting_resumption"
AWAITING_RESUMPTION_VERIFICATION = "awaiting_resumption_verification"
CLOSED = "closed"

PENDING = frozenset({
    DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT,
    AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SELF, CANCELLATION_PENDING,
    AWAITING_RESUMPTION_VERIFICATION,
})

MODIFIABLE = frozenset({
    DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT,
    AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SELF,
})

TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED, CLOSED})

ACTIVE_OCCUPANCY = frozenset({
    AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT,
    AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SELF, APPROVED,
    CANCELLATION_PENDING, AWAITING_RESUMPTION,
    AWAITING_RESUMPTION_VERIFICATION,
})

EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTIONING = "sanctioning_authority"
DIRECTOR = "director"
ADMIN = "leave_admin"
SYSTEM = "system"
VERIFIER = "verifier"


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


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)
    event: str = ""


def _t(frm, to, permission, actors, *guards, event=""):
    return Transition(frm, to, permission, frozenset(actors), guards, event)


TRANSITIONS: tuple[Transition, ...] = (
    # WF-EL-01 apply
    _t(DRAFT, DRAFT, "leave.application.create", {EMPLOYEE},
       "validation_failed", event="validation_failed"),
    _t(DRAFT, AWAITING_SUBSTITUTE, "leave.application.create", {EMPLOYEE},
       "valid", "substitute_required", event="submit"),
    _t(DRAFT, AWAITING_DIRECTOR_SELF, "leave.application.create", {EMPLOYEE},
       "valid", "no_substitute", "director_applicant", event="submit"),
    _t(DRAFT, AWAITING_UNIT_HEAD, "leave.application.create", {EMPLOYEE},
       "valid", "no_substitute", "normal_path", event="submit"),

    _t(AWAITING_SUBSTITUTE, AWAITING_DIRECTOR_SELF, "leave.substitute.review",
       {SUBSTITUTE}, "accepted", "director_applicant", event="substitute_accept"),
    _t(AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, "leave.substitute.review",
       {SUBSTITUTE}, "accepted", "normal_path", event="substitute_accept"),
    _t(AWAITING_SUBSTITUTE, AWAITING_SUBSTITUTE, "leave.substitute.review",
       {SUBSTITUTE}, "declined", event="substitute_decline"),

    _t(AWAITING_UNIT_HEAD, APPROVED, "leave.application.approve", {UNIT_HEAD},
       "cl_or_rh", "approve", event="unit_head_approve"),
    _t(AWAITING_UNIT_HEAD, REJECTED, "leave.application.approve", {UNIT_HEAD},
       "cl_or_rh", "reject", event="unit_head_reject"),
    _t(AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, "leave.application.review",
       {UNIT_HEAD}, "higher_sanction", "establishment_configured",
       event="unit_head_recommend"),
    _t(AWAITING_UNIT_HEAD, AWAITING_FINAL_SANCTION, "leave.application.review",
       {UNIT_HEAD}, "higher_sanction", "no_establishment",
       event="unit_head_recommend"),

    _t(AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, "leave.application.review",
       {ESTABLISHMENT}, "authority_resolved", event="establishment_route"),

    _t(AWAITING_FINAL_SANCTION, APPROVED, "leave.application.approve",
       {SANCTIONING, DIRECTOR}, "approve", event="final_approve"),
    _t(AWAITING_FINAL_SANCTION, REJECTED, "leave.application.approve",
       {SANCTIONING, DIRECTOR}, "reject", event="final_reject"),

    _t(AWAITING_DIRECTOR_SELF, APPROVED, "leave.application.approve", {DIRECTOR},
       "approve", event="director_self_approve"),
    _t(AWAITING_DIRECTOR_SELF, REJECTED, "leave.application.approve", {DIRECTOR},
       "reject", event="director_self_reject"),

    # WF-EL-02 withdraw (BR-EL-022)
    *(_t(s, WITHDRAWN, "leave.application.delete", {EMPLOYEE},
         "before_final_approval", event="withdraw")
      for s in MODIFIABLE),

    # WF-EL-03 cancellation (BR-EL-023)
    _t(APPROVED, CANCELLATION_PENDING, "leave.application.create", {EMPLOYEE},
       "not_started", event="request_cancellation"),
    _t(CANCELLATION_PENDING, CANCELLED, "leave.application.approve",
       {UNIT_HEAD, SANCTIONING, DIRECTOR, ESTABLISHMENT},
       "cancellation_approved", event="approve_cancellation"),
    _t(CANCELLATION_PENDING, APPROVED, "leave.application.approve",
       {UNIT_HEAD, SANCTIONING, DIRECTOR, ESTABLISHMENT},
       "cancellation_rejected", event="reject_cancellation"),

    # WF-EL-05 resumption (BR-EL-027/028)
    _t(APPROVED, AWAITING_RESUMPTION_VERIFICATION, "leave.application.create",
       {EMPLOYEE}, "resumable", event="submit_resumption"),
    _t(AWAITING_RESUMPTION, AWAITING_RESUMPTION_VERIFICATION,
       "leave.application.create", {EMPLOYEE}, "resumable",
       event="submit_resumption"),
    _t(AWAITING_RESUMPTION_VERIFICATION, AWAITING_RESUMPTION_VERIFICATION,
       "leave.application.review", {VERIFIER, UNIT_HEAD, ESTABLISHMENT},
       "not_verified", event="resumption_rejected"),
    _t(AWAITING_RESUMPTION_VERIFICATION, CLOSED, "leave.application.review",
       {VERIFIER, UNIT_HEAD, ESTABLISHMENT}, "verified",
       event="verify_resumption"),
)


def is_legal(frm: str, to: str) -> bool:
    return any(t.frm == frm and t.to == to for t in TRANSITIONS)


def resolve(frm: str, to: str, event: str | None = None) -> Transition:
    rows = [t for t in TRANSITIONS if t.frm == frm and t.to == to]
    if event:
        rows = [t for t in rows if t.event == event]
    if not rows:
        raise InvalidTransition(frm, to)
    return rows[0]


def pick(*, frm: str, event: str, actor_kind: str,
         facts: dict[str, bool]) -> Transition:
    rows = [t for t in TRANSITIONS if t.frm == frm and t.event == event]
    if not rows:
        raise InvalidTransition(frm, event)
    for t in rows:
        if actor_kind not in t.actors:
            continue
        if all(facts.get(g, False) for g in t.guards):
            return t
    raise GuardFailed(event, "No legal transition matched the current guards.")


def is_higher_sanction(category: str) -> bool:
    return category in HIGHER_SANCTION


def is_unit_head_final(category: str) -> bool:
    return category in UNIT_HEAD_FINAL
