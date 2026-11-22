"""Declarative state machine and transitions for quizzes and attempts."""

from __future__ import annotations


class QuizState:
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class AttemptState:
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AUTOSUBMITTED = "AUTOSUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    EVALUATED = "EVALUATED"


QUIZ_TRANSITIONS: dict[str, set[str]] = {
    QuizState.DRAFT: {QuizState.PUBLISHED},
    QuizState.PUBLISHED: {QuizState.CLOSED},
    QuizState.CLOSED: {QuizState.ARCHIVED},
    QuizState.ARCHIVED: set(),
}

ATTEMPT_TRANSITIONS: dict[str, set[str]] = {
    AttemptState.IN_PROGRESS: {
        AttemptState.SUBMITTED,
        AttemptState.AUTOSUBMITTED,
        AttemptState.UNDER_REVIEW,
        AttemptState.EVALUATED,
    },
    AttemptState.SUBMITTED: {AttemptState.UNDER_REVIEW, AttemptState.EVALUATED},
    AttemptState.AUTOSUBMITTED: {AttemptState.UNDER_REVIEW, AttemptState.EVALUATED},
    AttemptState.UNDER_REVIEW: {AttemptState.EVALUATED},
    AttemptState.EVALUATED: set(),
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is requested."""

    def __init__(self, entity_name: str, current_state: str, target_state: str):
        message = (
            f"Cannot transition {entity_name} from {current_state} to {target_state}. "
            "Please check current status and retry with a valid action."
        )
        super().__init__(message)


def transition_quiz(quiz, target_status: str) -> None:
    current = getattr(quiz, "status", None)
    allowed = QUIZ_TRANSITIONS.get(current, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError("quiz", current, target_status)
    quiz.status = target_status


def transition_attempt(attempt, target_status: str) -> None:
    current = getattr(attempt, "status", None)
    allowed = ATTEMPT_TRANSITIONS.get(current, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError("attempt", current, target_status)
    attempt.status = target_status
