"""The request state machine as data, from the Workflow Specification STTs.

One table serves new leave (CW-EL-01), cancellation (CW-EL-02) and extension
(CW-EL-03): they share states and differ only in where they enter and in what
the service does on approval. A pair missing from TRANSITIONS cannot happen.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class State(StrEnum):
    AWAITING_SUBSTITUTE = "awaiting_substitute"
    APPLICANT_ACTION = "applicant_action_required"
    AWAITING_UNIT_HEAD = "awaiting_unit_head"
    AWAITING_ESTABLISHMENT = "awaiting_establishment"
    AWAITING_FINAL = "awaiting_final_decision"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"


class Event(StrEnum):
    SUBSTITUTE_ACCEPT = "substitute_accept"
    SUBSTITUTE_ACCEPT_DIRECTOR = "substitute_accept_director"
    SUBSTITUTE_DECLINE = "substitute_decline"
    RENOMINATE = "renominate"
    UNIT_HEAD_APPROVE = "unit_head_approve"
    UNIT_HEAD_REJECT = "unit_head_reject"
    RECOMMEND_TO_ESTABLISHMENT = "recommend_to_establishment"
    RECOMMEND_TO_FINAL = "recommend_to_final"
    ESTABLISHMENT_ROUTE = "establishment_route"
    FINAL_APPROVE = "final_approve"
    FINAL_REJECT = "final_reject"
    WITHDRAW = "withdraw"
    MARK_CANCELLED = "mark_cancelled"


class Actor(StrEnum):
    APPLICANT = "applicant"
    SUBSTITUTE = "substitute"
    UNIT_HEAD = "unit_head"
    ESTABLISHMENT = "establishment"
    SANCTIONING = "sanctioning_authority"
    SYSTEM = "system"


S, E, A = State, Event, Actor

TRANSITIONS: dict[tuple[State, Event], tuple[Actor, State]] = {
    (S.AWAITING_SUBSTITUTE, E.SUBSTITUTE_ACCEPT): (A.SUBSTITUTE, S.AWAITING_UNIT_HEAD),
    (S.AWAITING_SUBSTITUTE, E.SUBSTITUTE_ACCEPT_DIRECTOR): (A.SUBSTITUTE, S.AWAITING_FINAL),
    (S.AWAITING_SUBSTITUTE, E.SUBSTITUTE_DECLINE): (A.SUBSTITUTE, S.APPLICANT_ACTION),
    (S.APPLICANT_ACTION, E.RENOMINATE): (A.APPLICANT, S.AWAITING_SUBSTITUTE),
    (S.AWAITING_UNIT_HEAD, E.UNIT_HEAD_APPROVE): (A.UNIT_HEAD, S.APPROVED),
    (S.AWAITING_UNIT_HEAD, E.UNIT_HEAD_REJECT): (A.UNIT_HEAD, S.REJECTED),
    (S.AWAITING_UNIT_HEAD, E.RECOMMEND_TO_ESTABLISHMENT): (A.UNIT_HEAD, S.AWAITING_ESTABLISHMENT),
    (S.AWAITING_UNIT_HEAD, E.RECOMMEND_TO_FINAL): (A.UNIT_HEAD, S.AWAITING_FINAL),
    (S.AWAITING_ESTABLISHMENT, E.ESTABLISHMENT_ROUTE): (A.ESTABLISHMENT, S.AWAITING_FINAL),
    (S.AWAITING_FINAL, E.FINAL_APPROVE): (A.SANCTIONING, S.APPROVED),
    (S.AWAITING_FINAL, E.FINAL_REJECT): (A.SANCTIONING, S.REJECTED),
    (S.APPROVED, E.MARK_CANCELLED): (A.SYSTEM, S.CANCELLED),
    **{(s, E.WITHDRAW): (A.APPLICANT, S.WITHDRAWN) for s in (
        S.AWAITING_SUBSTITUTE, S.APPLICANT_ACTION, S.AWAITING_UNIT_HEAD,
        S.AWAITING_ESTABLISHMENT, S.AWAITING_FINAL)},
}

PENDING = frozenset({S.AWAITING_SUBSTITUTE, S.APPLICANT_ACTION, S.AWAITING_UNIT_HEAD,
                     S.AWAITING_ESTABLISHMENT, S.AWAITING_FINAL})
HOLDS_DATES = PENDING | {S.APPROVED}

#: Whose turn it is in each pending state; drives the task inbox and SLA.
ASSIGNEE = {
    S.AWAITING_SUBSTITUTE: A.SUBSTITUTE,
    S.APPLICANT_ACTION: A.APPLICANT,
    S.AWAITING_UNIT_HEAD: A.UNIT_HEAD,
    S.AWAITING_ESTABLISHMENT: A.ESTABLISHMENT,
    S.AWAITING_FINAL: A.SANCTIONING,
}


class IllegalTransition(Exception):
    pass


class WrongActor(Exception):
    pass


def next_state(state: State, event: Event, actor: Actor) -> State:
    try:
        expected, target = TRANSITIONS[(state, event)]
    except KeyError as exc:
        raise IllegalTransition(
            f"A request that is {state.value.replace('_', ' ')} cannot take this action.") from exc
    if expected is not actor:
        raise WrongActor(f"This step belongs to the {expected.value.replace('_', ' ')}.")
    return target


@dataclass(frozen=True)
class Route:
    """BR-EL-016..020, already resolved against current configuration."""

    unit_head_final: bool
    establishment: bool
    director_self: bool


def entry_state(route: Route, *, has_substitute: bool) -> State:
    if has_substitute:
        return S.AWAITING_SUBSTITUTE
    return S.AWAITING_FINAL if route.director_self else S.AWAITING_UNIT_HEAD


def substitute_event(route: Route, accept: bool) -> Event:
    if not accept:
        return E.SUBSTITUTE_DECLINE
    return E.SUBSTITUTE_ACCEPT_DIRECTOR if route.director_self else E.SUBSTITUTE_ACCEPT


class Decision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"


def unit_head_event(route: Route, decision: Decision) -> Event:
    """BR-EL-016 decides; BR-EL-017 only recommends, and both outcomes move on."""
    if route.unit_head_final:
        if decision is Decision.APPROVE:
            return E.UNIT_HEAD_APPROVE
        if decision is Decision.REJECT:
            return E.UNIT_HEAD_REJECT
        raise IllegalTransition("For CL and RH the Unit Head approves or rejects.")
    if decision not in (Decision.RECOMMENDED, Decision.NOT_RECOMMENDED):
        raise IllegalTransition(
            "For SCL, EL, COL and VL the Unit Head records Recommended or Not Recommended.")
    return E.RECOMMEND_TO_ESTABLISHMENT if route.establishment else E.RECOMMEND_TO_FINAL
