"""Attempt selectors — read-only queries for attempts and responses."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.quiz.domain.state_machine import AttemptStatus
from modules.quiz.models import QuizAttempt


def attempts_for_quiz(quiz_id: int, principal) -> QuerySet[QuizAttempt]:
    """All attempts for a quiz — only the owning professor may see this."""
    return (
        QuizAttempt.objects.filter(quiz_id=quiz_id)
        .select_related("quiz")
        .order_by("-started_at")
    )


def my_attempts(principal) -> QuerySet[QuizAttempt]:
    """All of a student's own attempts."""
    return (
        QuizAttempt.objects.filter(user_id=principal.erp_user_id)
        .select_related("quiz")
        .order_by("-started_at")
    )


def released_results(principal) -> QuerySet[QuizAttempt]:
    """Student's attempts whose results have been released."""
    return (
        QuizAttempt.objects.filter(
            user_id=principal.erp_user_id,
            status=AttemptStatus.RELEASED,
        )
        .select_related("quiz")
        .order_by("-submitted_at")
    )


def attempt_detail_for_student(attempt_id: int, principal) -> QuizAttempt:
    """Single attempt owned by this student — raises DoesNotExist if not found."""
    return (
        QuizAttempt.objects.select_related("quiz")
        .prefetch_related("responses__question")
        .get(pk=attempt_id, user_id=principal.erp_user_id)
    )


def attempt_detail_for_professor(attempt_id: int, quiz_id: int, principal) -> QuizAttempt:
    """Single attempt for professor evaluation — scoped to professor's quiz."""
    return (
        QuizAttempt.objects.select_related("quiz")
        .prefetch_related("responses__question")
        .get(
            pk=attempt_id,
            quiz_id=quiz_id,
            quiz__created_by_user_id=principal.erp_user_id,
        )
    )
