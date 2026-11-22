"""Quiz domain — pure Python, no Django imports."""
from enum import StrEnum


class QuizStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    AVAILABLE = "available"
    CLOSED = "closed"
    ARCHIVED = "archived"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    PARTIALLY_EVALUATED = "partially_evaluated"
    EVALUATED = "evaluated"
    RELEASED = "released"


QUIZ_TERMINAL: frozenset[QuizStatus] = frozenset({QuizStatus.ARCHIVED})

ATTEMPT_TERMINAL: frozenset[AttemptStatus] = frozenset({AttemptStatus.RELEASED})

# (from_state, to_state) pairs that are allowed
QUIZ_TRANSITIONS: frozenset[tuple[QuizStatus, QuizStatus]] = frozenset({
    (QuizStatus.DRAFT, QuizStatus.SCHEDULED),
    (QuizStatus.DRAFT, QuizStatus.AVAILABLE),
    (QuizStatus.SCHEDULED, QuizStatus.AVAILABLE),
    (QuizStatus.AVAILABLE, QuizStatus.CLOSED),
    (QuizStatus.CLOSED, QuizStatus.ARCHIVED),
})

ATTEMPT_TRANSITIONS: frozenset[tuple[AttemptStatus, AttemptStatus]] = frozenset({
    (AttemptStatus.IN_PROGRESS, AttemptStatus.SUBMITTED),
    (AttemptStatus.SUBMITTED, AttemptStatus.EVALUATED),
    (AttemptStatus.SUBMITTED, AttemptStatus.PARTIALLY_EVALUATED),
    (AttemptStatus.PARTIALLY_EVALUATED, AttemptStatus.EVALUATED),
    (AttemptStatus.EVALUATED, AttemptStatus.RELEASED),
})


def validate_quiz_transition(from_status: str, to_status: str) -> None:
    """Raise InvalidQuizTransition if the transition is not allowed."""
    pair = (QuizStatus(from_status), QuizStatus(to_status))
    if pair not in QUIZ_TRANSITIONS:
        from modules.quiz.domain.errors import InvalidQuizTransition
        raise InvalidQuizTransition(
            f"Cannot transition quiz from '{from_status}' to '{to_status}'."
        )


def validate_attempt_transition(from_status: str, to_status: str) -> None:
    """Raise InvalidAttemptTransition if the transition is not allowed."""
    pair = (AttemptStatus(from_status), AttemptStatus(to_status))
    if pair not in ATTEMPT_TRANSITIONS:
        from modules.quiz.domain.errors import InvalidAttemptTransition
        raise InvalidAttemptTransition(
            f"Cannot transition attempt from '{from_status}' to '{to_status}'."
        )


def quiz_status_choices():
    return [(s.value, s.value.capitalize()) for s in QuizStatus]


def attempt_status_choices():
    return [(s.value, s.value.replace("_", " ").capitalize()) for s in AttemptStatus]
