"""Declarative Quiz, Attempt and Result lifecycle transitions.

The actor labels here describe specification actors only. Authentication,
permissions, course scoping and guard fact retrieval belong outside this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from modules.quiz.domain.errors import (
    ActorNotAllowed,
    GuardFailed,
    InvalidTransition,
)
from modules.quiz.domain.types import (
    AttemptStatus,
    DomainActor,
    QuizStatus,
    ResultStatus,
)


class QuizEvent(StrEnum):
    CREATE_DRAFT = "create draft"
    PUBLISH_NOW = "publish now"
    SCHEDULE = "schedule"
    START_BOUNDARY = "start boundary"
    CLOSE_BOUNDARY = "close boundary"
    ARCHIVE = "archive"
    HARD_DELETE_DRAFT = "hard-delete draft"


class AttemptEvent(StrEnum):
    START = "start attempt"
    SAVE_RESPONSE = "save response"
    MANUAL_SUBMIT = "confirmed manual submit"
    AUTO_SUBMIT_DEADLINE = "deadline reached / auto-submit"
    QUIZ_CLOSED = "quiz closes"


class ResultEvent(StrEnum):
    CREATE_ON_SUBMISSION = "create on submission"
    OBJECTIVE_COMPLETE = "objective complete"
    OBJECTIVE_PORTION_COMPLETE = "objective portion complete"
    SUBJECTIVE_FINALIZED = "subjective finalized"
    RELEASE = "release"


@dataclass(frozen=True)
class Transition[StateT: StrEnum, EventT: StrEnum]:
    """One permitted state/event/actor edge and its required guard facts."""

    source: StateT | None
    event: EventT
    actor: DomainActor
    target: StateT
    guards: tuple[str, ...] = ()


QUIZ_TRANSITIONS: tuple[Transition[QuizStatus, QuizEvent], ...] = (
    Transition(None, QuizEvent.CREATE_DRAFT, DomainActor.PROFESSOR, QuizStatus.DRAFT),
    Transition(
        QuizStatus.DRAFT,
        QuizEvent.PUBLISH_NOW,
        DomainActor.PROFESSOR,
        QuizStatus.AVAILABLE,
        ("valid_for_publication", "within_availability_window"),
    ),
    Transition(
        QuizStatus.DRAFT,
        QuizEvent.SCHEDULE,
        DomainActor.PROFESSOR,
        QuizStatus.SCHEDULED,
        ("valid_for_publication", "start_is_future"),
    ),
    Transition(
        QuizStatus.SCHEDULED,
        QuizEvent.START_BOUNDARY,
        DomainActor.SYSTEM,
        QuizStatus.AVAILABLE,
        ("start_boundary_reached", "before_close"),
    ),
    Transition(
        QuizStatus.AVAILABLE,
        QuizEvent.CLOSE_BOUNDARY,
        DomainActor.SYSTEM,
        QuizStatus.CLOSED,
        ("close_boundary_reached",),
    ),
    Transition(
        QuizStatus.CLOSED,
        QuizEvent.ARCHIVE,
        DomainActor.PROFESSOR,
        QuizStatus.ARCHIVED,
        ("archive_permitted",),
    ),
    Transition(
        QuizStatus.DRAFT,
        QuizEvent.HARD_DELETE_DRAFT,
        DomainActor.PROFESSOR,
        QuizStatus.DELETED,
        ("draft_with_zero_attempts",),
    ),
)

ATTEMPT_TRANSITIONS: tuple[Transition[AttemptStatus, AttemptEvent], ...] = (
    Transition(
        None,
        AttemptEvent.START,
        DomainActor.STUDENT,
        AttemptStatus.IN_PROGRESS,
        ("eligible", "available_before_close", "attempts_remaining"),
    ),
    Transition(
        AttemptStatus.IN_PROGRESS,
        AttemptEvent.SAVE_RESPONSE,
        DomainActor.STUDENT,
        AttemptStatus.IN_PROGRESS,
        ("owns_attempt", "before_deadline", "item_belongs_to_attempt"),
    ),
    Transition(
        AttemptStatus.IN_PROGRESS,
        AttemptEvent.MANUAL_SUBMIT,
        DomainActor.STUDENT,
        AttemptStatus.SUBMITTED,
        ("owns_attempt", "before_deadline", "submission_confirmed"),
    ),
    Transition(
        AttemptStatus.IN_PROGRESS,
        AttemptEvent.AUTO_SUBMIT_DEADLINE,
        DomainActor.SYSTEM,
        AttemptStatus.SUBMITTED,
        ("deadline_reached",),
    ),
    Transition(
        AttemptStatus.IN_PROGRESS,
        AttemptEvent.QUIZ_CLOSED,
        DomainActor.SYSTEM,
        AttemptStatus.IN_PROGRESS,
        ("close_boundary_reached",),
    ),
)

RESULT_TRANSITIONS: tuple[Transition[ResultStatus, ResultEvent], ...] = (
    Transition(
        None,
        ResultEvent.CREATE_ON_SUBMISSION,
        DomainActor.SYSTEM,
        ResultStatus.NOT_EVALUATED,
    ),
    Transition(
        ResultStatus.NOT_EVALUATED,
        ResultEvent.OBJECTIVE_COMPLETE,
        DomainActor.SYSTEM,
        ResultStatus.EVALUATED,
        ("objective_policy_settled", "all_responses_evaluated"),
    ),
    Transition(
        ResultStatus.NOT_EVALUATED,
        ResultEvent.OBJECTIVE_PORTION_COMPLETE,
        DomainActor.SYSTEM,
        ResultStatus.PARTIALLY_EVALUATED,
        ("objective_policy_settled", "subjective_responses_pending"),
    ),
    Transition(
        ResultStatus.NOT_EVALUATED,
        ResultEvent.SUBJECTIVE_FINALIZED,
        DomainActor.PROFESSOR,
        ResultStatus.EVALUATED,
        ("course_scope_verified", "marks_valid", "audit_recordable"),
    ),
    Transition(
        ResultStatus.PARTIALLY_EVALUATED,
        ResultEvent.SUBJECTIVE_FINALIZED,
        DomainActor.PROFESSOR,
        ResultStatus.EVALUATED,
        ("course_scope_verified", "all_subjective_marks_final", "audit_recordable"),
    ),
    Transition(
        ResultStatus.EVALUATED,
        ResultEvent.RELEASE,
        DomainActor.PROFESSOR,
        ResultStatus.RELEASED,
        ("course_scope_verified", "evaluation_complete", "visibility_policy_settled"),
    ),
)


def _resolve_transition[StateT: StrEnum, EventT: StrEnum](
    *,
    aggregate: str,
    transitions: tuple[Transition[StateT, EventT], ...],
    current: StateT | None,
    event: EventT,
    actor: DomainActor,
    guard_results: Mapping[str, bool] | None,
) -> StateT:
    """Resolve one edge and fail closed when a transition guard is absent."""

    edge = next(
        (
            candidate
            for candidate in transitions
            if candidate.source == current and candidate.event == event
        ),
        None,
    )
    if edge is None:
        raise InvalidTransition(aggregate, current.value if current else None, event.value)
    if edge.actor is not actor:
        raise ActorNotAllowed(actor.value, event.value)

    supplied_guards = guard_results or {}
    for guard in edge.guards:
        if supplied_guards.get(guard) is not True:
            raise GuardFailed(guard)
    return edge.target


def transition_quiz(
    current: QuizStatus | None,
    event: QuizEvent,
    actor: DomainActor,
    *,
    guard_results: Mapping[str, bool] | None = None,
) -> QuizStatus:
    """Return the next Quiz status; no database or IAM facts are fetched."""

    return _resolve_transition(
        aggregate="Quiz",
        transitions=QUIZ_TRANSITIONS,
        current=current,
        event=event,
        actor=actor,
        guard_results=guard_results,
    )


def transition_attempt(
    current: AttemptStatus | None,
    event: AttemptEvent,
    actor: DomainActor,
    *,
    guard_results: Mapping[str, bool] | None = None,
) -> AttemptStatus:
    """Return the next Attempt status; close leaves an active attempt active."""

    return _resolve_transition(
        aggregate="Attempt",
        transitions=ATTEMPT_TRANSITIONS,
        current=current,
        event=event,
        actor=actor,
        guard_results=guard_results,
    )


def transition_result(
    current: ResultStatus | None,
    event: ResultEvent,
    actor: DomainActor,
    *,
    guard_results: Mapping[str, bool] | None = None,
) -> ResultStatus:
    """Return the next Result status; unresolved scoring/release guards fail closed."""

    return _resolve_transition(
        aggregate="Result",
        transitions=RESULT_TRANSITIONS,
        current=current,
        event=event,
        actor=actor,
        guard_results=guard_results,
    )
