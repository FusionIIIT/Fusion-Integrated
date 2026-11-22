"""Scheduled work for quiz module.

Ids only in arguments, never ORM objects. Everything is idempotent.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import ExpressionWrapper, F, fields
from django.utils import timezone

log = logging.getLogger("fusion.quiz.tasks")


@shared_task(
    name="quiz.process_quiz_boundaries",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def process_quiz_boundaries() -> int:
    """Transition quiz states based on start/close boundaries (UC-QZ-018).

    - Scheduled → Available when start_at <= now
    - Available → Closed when close_at <= now
    """
    from modules.quiz.domain.state_machine import QuizStatus
    from modules.quiz.models import Quiz

    now = timezone.now()
    made_available = Quiz.objects.filter(
        status=QuizStatus.SCHEDULED,
        start_at__lte=now,
    ).update(status=QuizStatus.AVAILABLE)

    made_closed = Quiz.objects.filter(
        status=QuizStatus.AVAILABLE,
        close_at__lte=now,
    ).update(status=QuizStatus.CLOSED)

    total = made_available + made_closed
    if total:
        log.info(
            "quiz.boundaries.updated available=%d closed=%d",
            made_available,
            made_closed,
        )
    return total


@shared_task(
    name="quiz.auto_submit_expired_attempts",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def auto_submit_expired_attempts() -> int:
    """Auto-submit in-progress attempts whose time limit has expired (UC-QZ-011)."""
    from modules.quiz.domain.state_machine import AttemptStatus
    from modules.quiz.models import QuizAttempt
    from modules.quiz.services.attempts import auto_submit

    now = timezone.now()
    expired = QuizAttempt.objects.filter(
        status=AttemptStatus.IN_PROGRESS,
    ).select_related("quiz").annotate(
        deadline=ExpressionWrapper(
            F("started_at") + timedelta(minutes=1) * F("quiz__duration_minutes"),
            output_field=fields.DateTimeField(),
        )
    ).filter(deadline__lte=now)

    submitted_count = 0
    for attempt in expired:
        res = auto_submit(attempt_id=attempt.pk)
        if res is not None:
            submitted_count += 1

    if submitted_count:
        log.info("quiz.attempts.auto_submitted count=%d", submitted_count)
    return submitted_count
