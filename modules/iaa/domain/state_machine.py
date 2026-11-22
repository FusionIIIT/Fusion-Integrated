"""Declarative transition tables for records, anomalies and audit observations (CW-IAA-01..04)."""
from __future__ import annotations

from dataclasses import dataclass

from modules.iaa.domain.roles import (
    APPROVER_ACTOR,
    AUDITOR_ACTOR,
    FINANCE_ACTOR,
    OWNER,
    SYSTEM,
)

EXPENSE = "expense"
TA = "ta"
KINDS = (EXPENSE, TA)

DRAFT = "draft"
SUBMITTED = "submitted"
QUERY_RAISED = "query_raised"
QUERY_RESPONDED = "query_responded"
FINANCE_VALIDATED = "finance_validated"
VERIFIED = "verified"
APPROVAL_PENDING = "approval_pending"
ESCALATED = "escalated"
APPROVED = "approved"
REJECTED = "rejected"
RECORDED = "recorded"

RECORD_STATES = (DRAFT, SUBMITTED, QUERY_RAISED, QUERY_RESPONDED, FINANCE_VALIDATED, VERIFIED,
                 APPROVAL_PENDING, ESCALATED, APPROVED, REJECTED, RECORDED)
RECORD_TERMINAL = frozenset({REJECTED, RECORDED})
# States in which an approving authority holds the item.
AWAITING_AUTHORITY = frozenset({FINANCE_VALIDATED, APPROVAL_PENDING, ESCALATED})

SUBMIT = "submit"
RAISE_QUERY = "raise_query"
RESPOND_QUERY = "respond_query"
VALIDATE = "validate"
VERIFY = "verify"
VERIFY_FOR_APPROVAL = "verify_for_approval"
REJECT_POLICY = "reject_policy"
APPROVE_LEVEL = "approve_level"
APPROVE_FINAL = "approve_final"
REJECT = "reject"
ESCALATE = "escalate"
RECORD = "record"

ANOMALY_OPEN = "open"
ANOMALY_ESCALATED = "escalated"
ANOMALY_RESOLVED = "resolved"
ANOMALY_STATES = (ANOMALY_OPEN, ANOMALY_ESCALATED, ANOMALY_RESOLVED)
RESOLVE = "resolve"

OBS_OPEN = "open"
OBS_RESPONDED = "responded"
OBS_CLOSED = "closed"
OBSERVATION_STATES = (OBS_OPEN, OBS_RESPONDED, OBS_CLOSED)
RESPOND = "respond"
CLOSE = "close"
RETURN = "return"

RESOLVER = "resolver"
RESPONDENT = "respondent"


class InvalidTransition(Exception):
    def __init__(self, subject: str, frm: str, event: str):
        super().__init__(f"A {subject} in '{frm}' cannot take the action '{event}'.")
        self.subject, self.frm, self.event = subject, frm, event


class ActorNotAllowed(Exception):
    def __init__(self, subject: str, actor: str, event: str):
        super().__init__(f"A {actor} may not perform '{event}' on a {subject}.")
        self.subject, self.actor, self.event = subject, actor, event


@dataclass(frozen=True)
class Transition:
    kind: str
    frm: str
    event: str
    actor: str
    to: str
    ids: str


def _each(kinds, froms, event, actor, to, ids):
    return tuple(Transition(k, f, event, actor, to, ids) for k in kinds for f in froms)


RECORD_TRANSITIONS: tuple[Transition, ...] = (
    *_each((EXPENSE,), (DRAFT,), SUBMIT, OWNER, SUBMITTED, "IAA-UC-102"),
    *_each(KINDS, (SUBMITTED, QUERY_RESPONDED), RAISE_QUERY, FINANCE_ACTOR, QUERY_RAISED,
           "IAA-UC-103/402"),
    *_each(KINDS, (QUERY_RAISED,), RESPOND_QUERY, OWNER, QUERY_RESPONDED, "IAA-UC-104"),
    *_each((EXPENSE,), (SUBMITTED, QUERY_RESPONDED), VALIDATE, FINANCE_ACTOR, FINANCE_VALIDATED,
           "IAA-UC-103"),
    *_each((TA,), (SUBMITTED, QUERY_RESPONDED), VERIFY, FINANCE_ACTOR, VERIFIED, "IAA-UC-402"),
    *_each((TA,), (SUBMITTED, QUERY_RESPONDED), VERIFY_FOR_APPROVAL, FINANCE_ACTOR,
           APPROVAL_PENDING, "IAA-UC-402"),
    *_each((TA,), (SUBMITTED, QUERY_RESPONDED), REJECT_POLICY, FINANCE_ACTOR, REJECTED,
           "IAA-UC-402"),
    *_each((EXPENSE,), (FINANCE_VALIDATED, APPROVAL_PENDING, ESCALATED), APPROVE_LEVEL,
           APPROVER_ACTOR, APPROVAL_PENDING, "IAA-UC-201/202"),
    *_each((EXPENSE,), (FINANCE_VALIDATED, APPROVAL_PENDING, ESCALATED), APPROVE_FINAL,
           APPROVER_ACTOR, APPROVED, "IAA-UC-201/202"),
    *_each((EXPENSE,), (FINANCE_VALIDATED, APPROVAL_PENDING, ESCALATED), REJECT,
           APPROVER_ACTOR, REJECTED, "IAA-UC-201/202"),
    *_each((TA,), (APPROVAL_PENDING, ESCALATED), APPROVE_LEVEL, APPROVER_ACTOR,
           APPROVAL_PENDING, "IAA-UC-403/202"),
    *_each((TA,), (APPROVAL_PENDING, ESCALATED), APPROVE_FINAL, APPROVER_ACTOR, APPROVED,
           "IAA-UC-403/202"),
    *_each((TA,), (APPROVAL_PENDING, ESCALATED), REJECT, APPROVER_ACTOR, REJECTED,
           "IAA-UC-403/202"),
    *_each((EXPENSE,), (FINANCE_VALIDATED, APPROVAL_PENDING), ESCALATE, SYSTEM, ESCALATED,
           "IAA-UC-203"),
    *_each((TA,), (APPROVAL_PENDING,), ESCALATE, SYSTEM, ESCALATED, "IAA-UC-203"),
    *_each((EXPENSE,), (APPROVED,), RECORD, FINANCE_ACTOR, RECORDED, "IAA-UC-105"),
    *_each((TA,), (VERIFIED, APPROVED), RECORD, FINANCE_ACTOR, RECORDED, "IAA-UC-404"),
)

ANOMALY_TRANSITIONS: tuple[Transition, ...] = (
    Transition("anomaly", ANOMALY_OPEN, RESOLVE, RESOLVER, ANOMALY_RESOLVED, "IAA-UC-303"),
    Transition("anomaly", ANOMALY_OPEN, ESCALATE, RESOLVER, ANOMALY_ESCALATED, "IAA-UC-303"),
    Transition("anomaly", ANOMALY_ESCALATED, RESOLVE, RESOLVER, ANOMALY_RESOLVED, "IAA-UC-303"),
)

OBSERVATION_TRANSITIONS: tuple[Transition, ...] = (
    Transition("observation", OBS_OPEN, RESPOND, RESPONDENT, OBS_RESPONDED, "IAA-UC-502"),
    Transition("observation", OBS_RESPONDED, CLOSE, AUDITOR_ACTOR, OBS_CLOSED, "IAA-UC-503"),
    Transition("observation", OBS_RESPONDED, RETURN, AUDITOR_ACTOR, OBS_OPEN, "IAA-UC-503"),
)

_RECORDS = {(t.kind, t.frm, t.event): t for t in RECORD_TRANSITIONS}
_ANOMALIES = {(t.frm, t.event): t for t in ANOMALY_TRANSITIONS}
_OBSERVATIONS = {(t.frm, t.event): t for t in OBSERVATION_TRANSITIONS}


def resolve_record(kind: str, frm: str, event: str, actor: str) -> Transition:
    t = _RECORDS.get((kind, frm, event))
    if t is None:
        raise InvalidTransition("request" if kind == EXPENSE else "TA claim", frm, event)
    if actor != t.actor:
        raise ActorNotAllowed("request" if kind == EXPENSE else "TA claim", actor, event)
    return t


def resolve_anomaly(frm: str, event: str) -> Transition:
    t = _ANOMALIES.get((frm, event))
    if t is None:
        raise InvalidTransition("anomaly", frm, event)
    return t


def resolve_observation(frm: str, event: str, actor: str) -> Transition:
    t = _OBSERVATIONS.get((frm, event))
    if t is None:
        raise InvalidTransition("audit observation", frm, event)
    if actor != t.actor:
        raise ActorNotAllowed("audit observation", actor, event)
    return t


def record_events(kind: str, frm: str, actor: str | None = None) -> list[str]:
    return sorted(t.event for t in RECORD_TRANSITIONS
                  if t.kind == kind and t.frm == frm and (actor is None or t.actor == actor))
