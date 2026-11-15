"""State machine for Quizzing lifecycle."""

from core.api.exceptions import ConflictError
from modules.quizzing.models import QuizStatus, AttemptStatus


def transition_quiz(quiz, target_status: str) -> None:
    allowed = {QuizStatus.DRAFT: [QuizStatus.PUBLISHED], QuizStatus.PUBLISHED: [QuizStatus.CLOSED]}
    if target_status not in allowed.get(quiz.status, []):
        raise ConflictError(f"Cannot transition quiz from {quiz.status} to {target_status}")
    quiz.status = target_status


def transition_attempt(attempt, target_status: str) -> None:
    allowed = {
        AttemptStatus.IN_PROGRESS: [AttemptStatus.SUBMITTED, AttemptStatus.AUTOSUBMITTED],
        AttemptStatus.SUBMITTED: [AttemptStatus.EVALUATED],
        AttemptStatus.AUTOSUBMITTED: [AttemptStatus.EVALUATED],
    }
    if target_status not in allowed.get(attempt.status, []):
        raise ConflictError(f"Cannot transition attempt from {attempt.status} to {target_status}")
    attempt.status = target_status
