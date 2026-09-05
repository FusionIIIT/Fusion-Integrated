"""The states a leave request moves through, and who may move it.

Transcribed from the twelve basis workflows BW-EL-01 to BW-EL-12. The table is
the specification: a transition absent from it cannot be performed, so an
illegal move is not something the service layer has to remember to refuse.

Each row carries the workflow it came from so a reader can go back to the
document, and the use case that performs it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class State(StrEnum):
    DRAFT = "DRAFT"
    AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE"
    APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED"
    AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD"
    AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT"
    AWAITING_FINAL_SANCTION = "AWAITING_FINAL_SANCTION"
    AWAITING_SELF_SANCTION = "AWAITING_SELF_SANCTION"
    APPROVED_NOT_STARTED = "APPROVED_NOT_STARTED"
    ONGOING = "ONGOING"
    AWAITING_RESUMPTION = "AWAITING_RESUMPTION"
    AWAITING_RESUMPTION_VERIFICATION = "AWAITING_RESUMPTION_VERIFICATION"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"
    CANCELLATION_UNIT_HEAD = "CANCELLATION_UNIT_HEAD"
    CANCELLATION_ESTABLISHMENT = "CANCELLATION_ESTABLISHMENT"
    CANCELLATION_FINAL = "CANCELLATION_FINAL"
    EXTENSION_AWAITING_SUBSTITUTE = "EXTENSION_AWAITING_SUBSTITUTE"
    EXTENSION_APPLICANT_ACTION_REQUIRED = "EXTENSION_APPLICANT_ACTION_REQUIRED"
    EXTENSION_AWAITING_UNIT_HEAD = "EXTENSION_AWAITING_UNIT_HEAD"
    EXTENSION_AWAITING_ESTABLISHMENT = "EXTENSION_AWAITING_ESTABLISHMENT"
    EXTENSION_AWAITING_FINAL = "EXTENSION_AWAITING_FINAL"


class Actor(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    SUBSTITUTE = "SUBSTITUTE"
    UNIT_HEAD = "UNIT_HEAD"
    ESTABLISHMENT = "ESTABLISHMENT"
    SANCTIONING_AUTHORITY = "SANCTIONING_AUTHORITY"
    LEAVE_ADMINISTRATOR = "LEAVE_ADMINISTRATOR"
    SCHEDULER = "SCHEDULER"


class Event(StrEnum):
    SUBMIT = "SUBMIT"
    SUBSTITUTE_ACCEPT = "SUBSTITUTE_ACCEPT"
    SUBSTITUTE_DECLINE = "SUBSTITUTE_DECLINE"
    RENOMINATE = "RENOMINATE"
    UNIT_HEAD_APPROVE = "UNIT_HEAD_APPROVE"
    UNIT_HEAD_RECOMMEND = "UNIT_HEAD_RECOMMEND"
    UNIT_HEAD_REJECT = "UNIT_HEAD_REJECT"
    ROUTE = "ROUTE"
    SANCTION = "SANCTION"
    REFUSE = "REFUSE"
    WITHDRAW = "WITHDRAW"
    START = "START"
    REQUEST_CANCELLATION = "REQUEST_CANCELLATION"
    CANCELLATION_APPROVE = "CANCELLATION_APPROVE"
    CANCELLATION_REFUSE = "CANCELLATION_REFUSE"
    CANCELLATION_ROUTE = "CANCELLATION_ROUTE"
    REQUEST_EXTENSION = "REQUEST_EXTENSION"
    EXTENSION_GRANT = "EXTENSION_GRANT"
    EXTENSION_REFUSE = "EXTENSION_REFUSE"
    SUBMIT_RESUMPTION = "SUBMIT_RESUMPTION"
    RESUMPTION_QUERY = "RESUMPTION_QUERY"
    VERIFY_RESUMPTION = "VERIFY_RESUMPTION"
    REACH_END_DATE = "REACH_END_DATE"
    #: Not a workflow move. EL-UC-016 is record synchronisation, not approval.
    OFFLINE_RECORD = "OFFLINE_RECORD"


@dataclass(frozen=True)
class Transition:
    source: State
    event: Event
    target: State
    actor: Actor
    workflow: str
    use_case: str


S, E, A = State, Event, Actor

TRANSITIONS: tuple[Transition, ...] = (
    # BW-EL-01, BW-EL-02: substitute consent before review begins.
    Transition(
        S.DRAFT, E.SUBMIT, S.AWAITING_SUBSTITUTE,
        A.EMPLOYEE, "BW-EL-01", "EL-UC-001",
    ),
    Transition(
        S.DRAFT, E.SUBMIT, S.AWAITING_UNIT_HEAD,
        A.EMPLOYEE, "BW-EL-03", "EL-UC-001",
    ),
    Transition(
        S.DRAFT, E.SUBMIT, S.AWAITING_SELF_SANCTION,
        A.EMPLOYEE, "BW-EL-03", "EL-UC-001",
    ),
    Transition(
        S.AWAITING_SUBSTITUTE, E.SUBSTITUTE_ACCEPT, S.AWAITING_UNIT_HEAD,
        A.SUBSTITUTE, "BW-EL-01", "EL-UC-002",
    ),
    Transition(
        S.AWAITING_SUBSTITUTE, E.SUBSTITUTE_DECLINE, S.APPLICANT_ACTION_REQUIRED,
        A.SUBSTITUTE, "BW-EL-02", "EL-UC-002",
    ),
    Transition(
        S.APPLICANT_ACTION_REQUIRED, E.RENOMINATE, S.AWAITING_SUBSTITUTE,
        A.EMPLOYEE, "BW-EL-02", "EL-UC-006",
    ),
    Transition(
        S.APPLICANT_ACTION_REQUIRED, E.WITHDRAW, S.WITHDRAWN,
        A.EMPLOYEE, "BW-EL-02", "EL-UC-007",
    ),

    # BW-EL-03, BW-EL-04: review, routing and final sanction.
    Transition(
        S.AWAITING_UNIT_HEAD, E.UNIT_HEAD_APPROVE, S.APPROVED_NOT_STARTED,
        A.UNIT_HEAD, "BW-EL-03", "EL-UC-003",
    ),
    Transition(
        S.AWAITING_UNIT_HEAD, E.UNIT_HEAD_RECOMMEND, S.AWAITING_ESTABLISHMENT,
        A.UNIT_HEAD, "BW-EL-03", "EL-UC-003",
    ),
    Transition(
        S.AWAITING_UNIT_HEAD, E.UNIT_HEAD_RECOMMEND, S.AWAITING_FINAL_SANCTION,
        A.UNIT_HEAD, "BW-EL-03", "EL-UC-003",
    ),
    Transition(
        S.AWAITING_UNIT_HEAD, E.UNIT_HEAD_REJECT, S.REJECTED,
        A.UNIT_HEAD, "BW-EL-04", "EL-UC-003",
    ),
    Transition(
        S.AWAITING_ESTABLISHMENT, E.ROUTE, S.AWAITING_FINAL_SANCTION,
        A.ESTABLISHMENT, "BW-EL-03", "EL-UC-004",
    ),
    Transition(
        S.AWAITING_FINAL_SANCTION, E.SANCTION, S.APPROVED_NOT_STARTED,
        A.SANCTIONING_AUTHORITY, "BW-EL-03", "EL-UC-005",
    ),
    Transition(
        S.AWAITING_FINAL_SANCTION, E.REFUSE, S.REJECTED,
        A.SANCTIONING_AUTHORITY, "BW-EL-04", "EL-UC-005",
    ),
    # BR-EL-020. The Director sanctions their own leave.
    Transition(
        S.AWAITING_SELF_SANCTION, E.SANCTION, S.APPROVED_NOT_STARTED,
        A.SANCTIONING_AUTHORITY, "BW-EL-03", "EL-UC-005",
    ),
    Transition(
        S.AWAITING_SELF_SANCTION, E.REFUSE, S.REJECTED,
        A.SANCTIONING_AUTHORITY, "BW-EL-04", "EL-UC-005",
    ),

    # BR-EL-022. A pending request may be withdrawn at any point before approval.
    Transition(
        S.AWAITING_SUBSTITUTE, E.WITHDRAW, S.WITHDRAWN,
        A.EMPLOYEE, "BW-EL-01", "EL-UC-007",
    ),
    Transition(
        S.AWAITING_UNIT_HEAD, E.WITHDRAW, S.WITHDRAWN,
        A.EMPLOYEE, "BW-EL-03", "EL-UC-007",
    ),
    Transition(
        S.AWAITING_ESTABLISHMENT, E.WITHDRAW, S.WITHDRAWN,
        A.EMPLOYEE, "BW-EL-03", "EL-UC-007",
    ),
    Transition(
        S.AWAITING_FINAL_SANCTION, E.WITHDRAW, S.WITHDRAWN,
        A.EMPLOYEE, "BW-EL-03", "EL-UC-007",
    ),
    Transition(
        S.AWAITING_SELF_SANCTION, E.WITHDRAW, S.WITHDRAWN,
        A.EMPLOYEE, "BW-EL-03", "EL-UC-007",
    ),

    # BW-EL-05, BW-EL-06: cancelling approved leave that has not started.
    Transition(
        S.APPROVED_NOT_STARTED, E.REQUEST_CANCELLATION, S.CANCELLATION_UNIT_HEAD,
        A.EMPLOYEE, "BW-EL-05", "EL-UC-008",
    ),
    Transition(
        S.CANCELLATION_UNIT_HEAD, E.CANCELLATION_APPROVE, S.CANCELLED,
        A.UNIT_HEAD, "BW-EL-05", "EL-UC-008",
    ),
    Transition(
        S.CANCELLATION_UNIT_HEAD, E.CANCELLATION_ROUTE, S.CANCELLATION_ESTABLISHMENT,
        A.UNIT_HEAD, "BW-EL-05", "EL-UC-008",
    ),
    Transition(
        S.CANCELLATION_UNIT_HEAD, E.CANCELLATION_ROUTE, S.CANCELLATION_FINAL,
        A.UNIT_HEAD, "BW-EL-05", "EL-UC-008",
    ),
    Transition(
        S.CANCELLATION_UNIT_HEAD, E.CANCELLATION_REFUSE, S.APPROVED_NOT_STARTED,
        A.UNIT_HEAD, "BW-EL-06", "EL-UC-008",
    ),
    Transition(
        S.CANCELLATION_ESTABLISHMENT, E.CANCELLATION_ROUTE, S.CANCELLATION_FINAL,
        A.ESTABLISHMENT, "BW-EL-05", "EL-UC-004",
    ),
    Transition(
        S.CANCELLATION_FINAL, E.CANCELLATION_APPROVE, S.CANCELLED,
        A.SANCTIONING_AUTHORITY, "BW-EL-05", "EL-UC-005",
    ),
    Transition(
        S.CANCELLATION_FINAL, E.CANCELLATION_REFUSE, S.APPROVED_NOT_STARTED,
        A.SANCTIONING_AUTHORITY, "BW-EL-06", "EL-UC-005",
    ),

    # BW-EL-07, BW-EL-08: extending leave already running.
    Transition(
        S.APPROVED_NOT_STARTED, E.START, S.ONGOING,
        A.SCHEDULER, "BW-EL-09", "EL-UC-010",
    ),
    Transition(
        S.ONGOING, E.REQUEST_EXTENSION, S.EXTENSION_AWAITING_SUBSTITUTE,
        A.EMPLOYEE, "BW-EL-07", "EL-UC-009",
    ),
    Transition(
        S.ONGOING, E.REQUEST_EXTENSION, S.EXTENSION_AWAITING_UNIT_HEAD,
        A.EMPLOYEE, "BW-EL-07", "EL-UC-009",
    ),
    Transition(
        S.EXTENSION_AWAITING_SUBSTITUTE, E.SUBSTITUTE_ACCEPT, S.EXTENSION_AWAITING_UNIT_HEAD,
        A.SUBSTITUTE, "BW-EL-07", "EL-UC-002",
    ),
    Transition(
        S.EXTENSION_AWAITING_SUBSTITUTE, E.SUBSTITUTE_DECLINE,
        S.EXTENSION_APPLICANT_ACTION_REQUIRED,
        A.SUBSTITUTE, "BW-EL-07", "EL-UC-002",
    ),
    # Derived, not transcribed. BW-EL-07 row 4 enters Extension Applicant Action
    # Required and no row leaves it, which strands the request. The main flow
    # settles the same situation in BW-EL-02 and BW-EL-11/12 by letting the
    # applicant renominate or give up, so the same two exits are provided here.
    # Withdrawing abandons the extension only; the leave already running is
    # untouched, matching the rejected-extension outcome in row 9.
    Transition(
        S.EXTENSION_APPLICANT_ACTION_REQUIRED, E.RENOMINATE,
        S.EXTENSION_AWAITING_SUBSTITUTE,
        A.EMPLOYEE, "BW-EL-07 (derived)", "EL-UC-006",
    ),
    Transition(
        S.EXTENSION_APPLICANT_ACTION_REQUIRED, E.WITHDRAW, S.ONGOING,
        A.EMPLOYEE, "BW-EL-07 (derived)", "EL-UC-007",
    ),
    Transition(
        S.EXTENSION_AWAITING_UNIT_HEAD, E.UNIT_HEAD_RECOMMEND, S.EXTENSION_AWAITING_ESTABLISHMENT,
        A.UNIT_HEAD, "BW-EL-07", "EL-UC-003",
    ),
    Transition(
        S.EXTENSION_AWAITING_UNIT_HEAD, E.UNIT_HEAD_RECOMMEND, S.EXTENSION_AWAITING_FINAL,
        A.UNIT_HEAD, "BW-EL-07", "EL-UC-003",
    ),
    Transition(
        S.EXTENSION_AWAITING_ESTABLISHMENT, E.ROUTE, S.EXTENSION_AWAITING_FINAL,
        A.ESTABLISHMENT, "BW-EL-07", "EL-UC-004",
    ),
    Transition(
        S.EXTENSION_AWAITING_FINAL, E.EXTENSION_GRANT, S.ONGOING,
        A.SANCTIONING_AUTHORITY, "BW-EL-07", "EL-UC-005",
    ),
    Transition(
        S.EXTENSION_AWAITING_FINAL, E.EXTENSION_REFUSE, S.ONGOING,
        A.SANCTIONING_AUTHORITY, "BW-EL-08", "EL-UC-005",
    ),

    # BW-EL-09, BW-EL-10: resumption, whether on time or early.
    Transition(
        S.ONGOING, E.REACH_END_DATE, S.AWAITING_RESUMPTION,
        A.SCHEDULER, "BW-EL-09", "EL-UC-010",
    ),
    Transition(
        S.ONGOING, E.SUBMIT_RESUMPTION, S.AWAITING_RESUMPTION_VERIFICATION,
        A.EMPLOYEE, "BW-EL-10", "EL-UC-010",
    ),
    Transition(
        S.AWAITING_RESUMPTION, E.SUBMIT_RESUMPTION, S.AWAITING_RESUMPTION_VERIFICATION,
        A.EMPLOYEE, "BW-EL-09", "EL-UC-010",
    ),
    Transition(
        S.AWAITING_RESUMPTION_VERIFICATION, E.RESUMPTION_QUERY, S.AWAITING_RESUMPTION_VERIFICATION,
        A.ESTABLISHMENT, "BW-EL-09", "EL-UC-011",
    ),
    Transition(
        S.AWAITING_RESUMPTION_VERIFICATION, E.VERIFY_RESUMPTION, S.CLOSED,
        A.ESTABLISHMENT, "BW-EL-09", "EL-UC-011",
    ),
)

#: BR-EL-024. Cancellation is terminal, so an approved leave is never edited
#: in place -- revised leave is a fresh application, which is why CW-EL-01 is
#: named as the related workflow rather than a branch of cancellation.
TERMINAL: frozenset[State] = frozenset(
    {State.CLOSED, State.REJECTED, State.WITHDRAWN, State.CANCELLED}
)

_INDEX: dict[tuple[State, Event], tuple[Transition, ...]] = {}
for _t in TRANSITIONS:
    _INDEX.setdefault((_t.source, _t.event), ())
    _INDEX[(_t.source, _t.event)] += (_t,)


class IllegalTransition(Exception):
    """The move is not in the table, so it is not a move this system makes."""


def permitted(source: State, event: Event) -> tuple[Transition, ...]:
    return _INDEX.get((source, event), ())


def resolve(source: State, event: Event, target: State | None = None) -> Transition:
    """The transition to apply, or a refusal.

    Several rows share a source and event and differ only in target, because the
    hierarchy decides where a recommendation goes next. The caller supplies the
    target it resolved from the authority configuration.
    """
    options = permitted(source, event)
    if not options:
        raise IllegalTransition(f"{event.value} is not permitted from {source.value}")
    if target is None:
        if len(options) > 1:
            raise IllegalTransition(
                f"{event.value} from {source.value} needs a target: "
                + ", ".join(o.target.value for o in options)
            )
        return options[0]
    for option in options:
        if option.target is target:
            return option
    raise IllegalTransition(
        f"{event.value} from {source.value} cannot reach {target.value}"
    )


def is_terminal(state: State) -> bool:
    return state in TERMINAL
