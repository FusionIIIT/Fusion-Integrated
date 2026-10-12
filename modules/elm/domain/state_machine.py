"""The leave request state machine (WF-EL-01..05).

A declarative table, so an illegal move cannot be expressed. Branching events
list every target they may reach; the service picks one from the route and
`resolve` refuses anything outside that set.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.elm.domain import permissions as p
from modules.elm.domain import routing as r

NEW = "new"
AWAITING_SUBSTITUTE = "awaiting_substitute"
SUBSTITUTE_DECLINED = "substitute_declined"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_SANCTION = "awaiting_sanction"
AWAITING_DIRECTOR = "awaiting_director"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCELLATION_PENDING = "cancellation_pending"
CANCELLED = "cancelled"
RESUMPTION_PENDING = "resumption_pending"
CLOSED = "closed"

STATES = (AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINED, AWAITING_UNIT_HEAD,
          AWAITING_ESTABLISHMENT, AWAITING_SANCTION, AWAITING_DIRECTOR,
          APPROVED, REJECTED, WITHDRAWN, CANCELLATION_PENDING, CANCELLED,
          RESUMPTION_PENDING, CLOSED)

PENDING = frozenset({AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINED, AWAITING_UNIT_HEAD,
                     AWAITING_ESTABLISHMENT, AWAITING_SANCTION, AWAITING_DIRECTOR})
#: Leave that occupies dates for BR-EL-012 and BR-EL-014.
ACTIVE = PENDING | {APPROVED, CANCELLATION_PENDING, RESUMPTION_PENDING, CLOSED}
TERMINAL = frozenset({REJECTED, WITHDRAWN, CANCELLED, CLOSED})

STATE_FOR_STEP = {
    r.UNIT_HEAD: AWAITING_UNIT_HEAD,
    r.ESTABLISHMENT: AWAITING_ESTABLISHMENT,
    r.SANCTION: AWAITING_SANCTION,
    r.DIRECTOR: AWAITING_DIRECTOR,
}
ROUTING_ENTRY = frozenset({AWAITING_UNIT_HEAD, AWAITING_DIRECTOR})

EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTIONER = "sanctioner"
DIRECTOR = "director"
VERIFIER = "verifier"
ADMIN = "admin"

SUBMIT = "submit"
SUBSTITUTE_ACCEPT = "substitute_accept"
SUBSTITUTE_DECLINE = "substitute_decline"
RENOMINATE = "renominate"
MODIFY = "modify"
WITHDRAW = "withdraw"
APPROVE = "approve"
REJECT = "reject"
RECOMMEND = "recommend"
NOT_RECOMMEND = "not_recommend"
FORWARD = "forward"
REQUEST_CANCELLATION = "request_cancellation"
CANCEL_ADVANCE = "cancel_advance"
CANCEL_APPROVE = "cancel_approve"
CANCEL_REJECT = "cancel_reject"
SUBMIT_RESUMPTION = "submit_resumption"
VERIFY_RESUMPTION = "verify_resumption"
RECORD_OFFLINE = "record_offline"


class InvalidTransition(Exception):
    def __init__(self, frm: str, event: str, to: str | None = None):
        super().__init__(f"A request in {frm!r} cannot take {event!r}"
                         + (f" to {to!r}." if to else "."))
        self.frm, self.event, self.to = frm, event, to


class ActorNotAllowed(Exception):
    def __init__(self, actor: str, frm: str, event: str):
        super().__init__(f"A {actor} may not {event} a request in {frm!r}.")
        self.actor, self.frm, self.event = actor, frm, event


@dataclass(frozen=True)
class Transition:
    frm: str
    event: str
    targets: frozenset[str]
    actor: str
    permission: str


def _t(frm, event, targets, actor, permission):
    return Transition(frm, event, frozenset(targets), actor, permission)


_ENTRY = (AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_DIRECTOR)
_PENDING_ORDERED = (AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINED, AWAITING_UNIT_HEAD,
                    AWAITING_ESTABLISHMENT, AWAITING_SANCTION, AWAITING_DIRECTOR)

TRANSITIONS: tuple[Transition, ...] = (
    _t(NEW, SUBMIT, _ENTRY, EMPLOYEE, p.P_CREATE),
    _t(NEW, RECORD_OFFLINE, (APPROVED,), ADMIN, p.P_OFFLINE),

    _t(AWAITING_SUBSTITUTE, SUBSTITUTE_ACCEPT, (AWAITING_UNIT_HEAD, AWAITING_DIRECTOR),
       SUBSTITUTE, p.P_SUBSTITUTE),
    _t(AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINE, (SUBSTITUTE_DECLINED,),
       SUBSTITUTE, p.P_SUBSTITUTE),
    _t(SUBSTITUTE_DECLINED, RENOMINATE, (AWAITING_SUBSTITUTE,), EMPLOYEE, p.P_UPDATE),

    *(_t(s, MODIFY, _ENTRY, EMPLOYEE, p.P_UPDATE) for s in _PENDING_ORDERED),
    *(_t(s, WITHDRAW, (WITHDRAWN,), EMPLOYEE, p.P_WITHDRAW) for s in _PENDING_ORDERED),

    _t(AWAITING_UNIT_HEAD, APPROVE, (APPROVED,), UNIT_HEAD, p.P_APPROVE),
    _t(AWAITING_UNIT_HEAD, REJECT, (REJECTED,), UNIT_HEAD, p.P_APPROVE),
    _t(AWAITING_UNIT_HEAD, RECOMMEND, (AWAITING_ESTABLISHMENT, AWAITING_SANCTION),
       UNIT_HEAD, p.P_REVIEW),
    _t(AWAITING_UNIT_HEAD, NOT_RECOMMEND, (AWAITING_ESTABLISHMENT, AWAITING_SANCTION),
       UNIT_HEAD, p.P_REVIEW),
    _t(AWAITING_ESTABLISHMENT, FORWARD, (AWAITING_SANCTION,), ESTABLISHMENT, p.P_REVIEW),
    _t(AWAITING_SANCTION, APPROVE, (APPROVED,), SANCTIONER, p.P_APPROVE),
    _t(AWAITING_SANCTION, REJECT, (REJECTED,), SANCTIONER, p.P_APPROVE),
    _t(AWAITING_DIRECTOR, APPROVE, (APPROVED,), DIRECTOR, p.P_APPROVE),
    _t(AWAITING_DIRECTOR, REJECT, (REJECTED,), DIRECTOR, p.P_APPROVE),

    _t(APPROVED, REQUEST_CANCELLATION, (CANCELLATION_PENDING,), EMPLOYEE, p.P_UPDATE),
    *(_t(CANCELLATION_PENDING, CANCEL_ADVANCE, (CANCELLATION_PENDING,), a, p.P_REVIEW)
      for a in (UNIT_HEAD, ESTABLISHMENT)),
    *(_t(CANCELLATION_PENDING, CANCEL_APPROVE, (CANCELLED,), a, p.P_APPROVE)
      for a in (UNIT_HEAD, SANCTIONER, DIRECTOR)),
    *(_t(CANCELLATION_PENDING, CANCEL_REJECT, (APPROVED,), a, p.P_APPROVE)
      for a in (UNIT_HEAD, SANCTIONER, DIRECTOR)),

    _t(APPROVED, SUBMIT_RESUMPTION, (RESUMPTION_PENDING,), EMPLOYEE, p.P_UPDATE),
    _t(RESUMPTION_PENDING, VERIFY_RESUMPTION, (CLOSED,), VERIFIER, p.P_RESUMPTION),
)

_INDEX: dict[tuple[str, str, str], Transition] = {
    (t.frm, t.event, t.actor): t for t in TRANSITIONS}


def resolve(frm: str, event: str, actor: str, to: str) -> Transition:
    t = _INDEX.get((frm, event, actor))
    if t is None:
        if any(k[0] == frm and k[1] == event for k in _INDEX):
            raise ActorNotAllowed(actor, frm, event)
        raise InvalidTransition(frm, event)
    if to not in t.targets:
        raise InvalidTransition(frm, event, to)
    return t


def events_from(frm: str, actor: str | None = None) -> list[str]:
    return sorted({t.event for t in TRANSITIONS
                   if t.frm == frm and (actor is None or t.actor == actor)})


#: Which decisions each routed step may record, per category family.
def decision_events(step: str, unit_head_final: bool, cancelling: bool) -> tuple[str, ...]:
    if cancelling:
        if step == r.UNIT_HEAD and not unit_head_final:
            return (CANCEL_ADVANCE,)
        if step == r.ESTABLISHMENT:
            return (CANCEL_ADVANCE,)
        return (CANCEL_APPROVE, CANCEL_REJECT)
    if step == r.UNIT_HEAD:
        return (APPROVE, REJECT) if unit_head_final else (RECOMMEND, NOT_RECOMMEND)
    if step == r.ESTABLISHMENT:
        return (FORWARD,)
    return (APPROVE, REJECT)


ACTOR_FOR_STEP = {
    r.UNIT_HEAD: UNIT_HEAD,
    r.ESTABLISHMENT: ESTABLISHMENT,
    r.SANCTION: SANCTIONER,
    r.DIRECTOR: DIRECTOR,
}
