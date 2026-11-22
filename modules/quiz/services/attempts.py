"""Attempt lifecycle services — start, respond, submit, auto-submit."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.quiz.domain.errors import (
    AttemptAlreadySubmitted,
    AttemptLimitExceeded,
    AttemptNotActive,
    QuizNotAvailable,
)
from modules.quiz.domain.evaluation import evaluate_objective
from modules.quiz.domain.state_machine import AttemptStatus, QuizStatus
from modules.quiz.models import AttemptResponse, Quiz, QuizAttempt, QuizAuditLog

logger = logging.getLogger("fusion.quiz")


def start_attempt(*, quiz_id: int, principal) -> QuizAttempt:
    """Start a new attempt — validates eligibility and attempt limit (BR-QZ-003/008)."""
    now = timezone.now()
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(pk=quiz_id)

        # Quiz must be available (BR-QZ-006)
        if quiz.status != QuizStatus.AVAILABLE:
            raise QuizNotAvailable("This quiz is not currently available.")
        if quiz.start_at and quiz.start_at > now:
            raise QuizNotAvailable("This quiz has not started yet.")
        if quiz.close_at and quiz.close_at <= now:
            raise QuizNotAvailable("This quiz has closed.")

        user_id = principal.erp_user_id

        # Count completed attempts (BR-QZ-008)
        completed = QuizAttempt.objects.filter(
            quiz=quiz, user_id=user_id
        ).exclude(status=AttemptStatus.IN_PROGRESS).count()

        if completed >= quiz.max_attempts:
            raise AttemptLimitExceeded(
                f"You have used all {quiz.max_attempts} permitted attempt(s)."
            )

        attempt_number = completed + 1

        # Create the attempt
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user_id=user_id,
            status=AttemptStatus.IN_PROGRESS,
            started_at=now,
            attempt_number=attempt_number,
        )

        # Pre-create response placeholders for every question
        questions = list(quiz.questions.order_by("order", "id"))
        AttemptResponse.objects.bulk_create([
            AttemptResponse(attempt=attempt, question=q)
            for q in questions
        ])

        QuizAuditLog.objects.create(
            quiz=quiz,
            attempt=attempt,
            action="attempt_started",
            actor_user_id=user_id,
            detail={"attempt_number": attempt_number},
        )
    return attempt


def save_response(*, attempt_id: int, question_id: int,
                  response, principal) -> AttemptResponse:
    """Save/update a response during an active attempt (BR-QZ-015)."""
    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().get(
            pk=attempt_id, user_id=principal.erp_user_id
        )
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise AttemptAlreadySubmitted(
                "Cannot modify a submitted attempt (BR-QZ-016)."
            )

        ar, _ = AttemptResponse.objects.update_or_create(
            attempt=attempt,
            question_id=question_id,
            defaults={"response": response},
        )
    return ar


def submit_attempt(*, attempt_id: int, principal) -> QuizAttempt:
    """Manually submit an active attempt (UC-QZ-010)."""
    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().select_related("quiz").get(
            pk=attempt_id, user_id=principal.erp_user_id
        )
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise AttemptNotActive("Attempt is not in progress.")

        now = timezone.now()
        attempt.submitted_at = now
        attempt.time_taken_seconds = int(
            (now - attempt.started_at).total_seconds()
        )
        attempt.status = AttemptStatus.SUBMITTED
        attempt.save(update_fields=["status", "submitted_at", "time_taken_seconds"])

        QuizAuditLog.objects.create(
            quiz=attempt.quiz,
            attempt=attempt,
            action="attempt_submitted",
            actor_user_id=principal.erp_user_id,
        )

    # Auto-evaluate objective questions outside the lock
    _auto_evaluate_objective(attempt)
    return attempt


def auto_submit(*, attempt_id: int) -> QuizAttempt | None:
    """System auto-submit for time-expired attempt (UC-QZ-011 / BR-QZ-017)."""
    with transaction.atomic():
        try:
            attempt = QuizAttempt.objects.select_for_update().select_related(
                "quiz"
            ).get(pk=attempt_id, status=AttemptStatus.IN_PROGRESS)
        except QuizAttempt.DoesNotExist:
            return None  # Already submitted, skip

        now = timezone.now()
        attempt.submitted_at = now
        attempt.time_taken_seconds = int(
            (now - attempt.started_at).total_seconds()
        )
        attempt.status = AttemptStatus.SUBMITTED
        attempt.save(update_fields=["status", "submitted_at", "time_taken_seconds"])

        QuizAuditLog.objects.create(
            quiz=attempt.quiz,
            attempt=attempt,
            action="attempt_auto_submitted",
            actor_user_id=None,
            detail={"reason": "time_expired"},
        )

    _auto_evaluate_objective(attempt)
    return attempt


def _auto_evaluate_objective(attempt: QuizAttempt) -> None:
    """Evaluate all objective responses after submission (UC-QZ-012)."""
    quiz = attempt.quiz
    responses = list(
        AttemptResponse.objects.select_related("question").filter(attempt=attempt)
    )

    has_subjective = False
    total_objective_score = Decimal("0")

    updates = []
    for ar in responses:
        q = ar.question
        if q.question_type == "short":
            has_subjective = True
            continue  # Needs professor evaluation

        is_correct, marks = evaluate_objective(
            question_type=q.question_type,
            correct_answer=q.correct_answer,
            student_response=ar.response,
            marks=q.marks,
            negative_marks=q.negative_marks,
            negative_marking_enabled=quiz.negative_marking,
        )
        ar.is_correct = is_correct
        ar.marks_obtained = marks
        updates.append(ar)
        if marks is not None:
            total_objective_score += marks

    if updates:
        AttemptResponse.objects.bulk_update(updates, ["is_correct", "marks_obtained"])

    # Determine final attempt status
    with transaction.atomic():
        attempt_fresh = QuizAttempt.objects.select_for_update().get(pk=attempt.pk)
        if has_subjective:
            attempt_fresh.status = AttemptStatus.PARTIALLY_EVALUATED
        else:
            # Fully evaluated — compute final score
            attempt_fresh.score = total_objective_score
            if quiz.max_marks and quiz.max_marks > 0:
                attempt_fresh.percentage = (
                    total_objective_score / quiz.max_marks * 100
                ).quantize(Decimal("0.01"))
            if quiz.passing_marks is not None:
                attempt_fresh.passed = total_objective_score >= quiz.passing_marks
            attempt_fresh.status = AttemptStatus.EVALUATED
        attempt_fresh.save(
            update_fields=["status", "score", "percentage", "passed"]
        )
