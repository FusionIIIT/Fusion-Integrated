"""Bounded, retry-safe asynchronous Quiz lifecycle work."""

from __future__ import annotations

import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger("fusion.quiz.tasks")

DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 500


def _batch_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("Task batch limit must be a positive integer.")
    return min(limit, MAX_BATCH_SIZE)


@shared_task(
    name="quiz.tasks.auto_submit_expired_attempts",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=12,
    time_limit=14,
)
def auto_submit_expired_attempts(limit: int = DEFAULT_BATCH_SIZE) -> int:
    """Submit a bounded batch of attempts whose server deadlines have passed."""

    from modules.quiz.models import Attempt
    from modules.quiz.services.attempts import auto_submit_expired_attempt

    batch_size = _batch_limit(limit)
    server_now = timezone.now()
    due_ids = list(
        Attempt.objects.filter(status="in_progress", deadline_at__lte=server_now)
        .order_by("deadline_at", "pk")
        .values_list("pk", flat=True)[:batch_size]
    )
    processed = sum(auto_submit_expired_attempt(attempt_id=attempt_id) for attempt_id in due_ids)
    if processed:
        logger.info("quiz.attempts.auto_submitted count=%d", processed)
    return processed


@shared_task(
    name="quiz.tasks.process_quiz_boundaries",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=12,
    time_limit=14,
)
def process_quiz_boundaries(limit: int = DEFAULT_BATCH_SIZE) -> int:
    """Apply due Scheduled→Available and Available→Closed transitions."""

    from modules.quiz.models import Quiz
    from modules.quiz.services.lifecycle import process_quiz_boundary

    batch_size = _batch_limit(limit)
    server_now = timezone.now()
    due_boundary = Q(status="scheduled", start_at__lte=server_now) | Q(
        status="available", close_at__lte=server_now
    )
    due_ids = list(
        Quiz.objects.filter(due_boundary)
        .order_by("start_at", "close_at", "pk")
        .values_list("pk", flat=True)[:batch_size]
    )
    processed = sum(process_quiz_boundary(quiz_id=quiz_id) for quiz_id in due_ids)
    if processed:
        logger.info("quiz.boundaries.processed count=%d", processed)
    return processed
