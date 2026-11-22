"""Celery background tasks for the Quizzing module."""

from celery import shared_task
from django.utils import timezone

from modules.quizzing.domain.rules import is_attempt_expired
from modules.quizzing.models import AttemptStatus, QuizAttempt
from modules.quizzing.services.quiz_service import QuizService


@shared_task
def auto_submit_expired_attempts() -> int:
    """Periodic task to sweep and auto-submit idle expired attempts (BR-QZ-017)."""
    now = timezone.now()
    active_attempts = QuizAttempt.objects.filter(
        status=AttemptStatus.IN_PROGRESS
    ).select_related("quiz")

    count = 0
    for attempt in active_attempts:
        if is_attempt_expired(
            attempt.started_at,
            attempt.quiz.duration_minutes,
            attempt.quiz.end_time,
            now,
        ):
            QuizService.submit_attempt(str(attempt.id), autosubmit=True)
            count += 1
    return count
