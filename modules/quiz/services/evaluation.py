"""Evaluation and result-release services (CW-QZ-03)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.quiz.domain.errors import EvaluationError
from modules.quiz.domain.state_machine import AttemptStatus
from modules.quiz.models import AttemptResponse, QuizAttempt, QuizAuditLog


def evaluate_subjective(*, attempt_id: int, principal,
                        response_evaluations: list[dict]) -> QuizAttempt:
    """Professor finalizes marks/feedback for subjective responses (UC-QZ-013).

    response_evaluations: list of {response_id, marks_obtained, professor_feedback}
    """
    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().select_related("quiz").get(
            pk=attempt_id,
            quiz__created_by_user_id=principal.erp_user_id,
        )
        allowed = {AttemptStatus.SUBMITTED, AttemptStatus.PARTIALLY_EVALUATED}
        if attempt.status not in allowed:
            raise EvaluationError(
                f"Cannot evaluate attempt in '{attempt.status}' status."
            )

        now = timezone.now()
        for ev in response_evaluations:
            resp_id = ev["response_id"]
            marks = ev.get("marks_obtained")
            feedback = ev.get("professor_feedback", "")
            ai_suggested = ev.get("ai_suggested_marks")

            AttemptResponse.objects.filter(pk=resp_id, attempt=attempt).update(
                marks_obtained=marks,
                professor_feedback=feedback,
                ai_suggested_marks=ai_suggested,
                evaluated_by_user_id=principal.erp_user_id,
                evaluated_at=now,
            )

        # Recalculate total score
        responses = list(AttemptResponse.objects.filter(attempt=attempt))
        total = sum(
            (r.marks_obtained or Decimal("0")) for r in responses
        )

        quiz = attempt.quiz
        attempt.score = total
        if quiz.max_marks and quiz.max_marks > 0:
            attempt.percentage = (total / quiz.max_marks * 100).quantize(
                Decimal("0.01")
            )
        if quiz.passing_marks is not None:
            attempt.passed = total >= quiz.passing_marks

        attempt.status = AttemptStatus.EVALUATED
        attempt.save(update_fields=["status", "score", "percentage", "passed"])

        QuizAuditLog.objects.create(
            quiz=quiz,
            attempt=attempt,
            action="subjective_evaluated",
            actor_user_id=principal.erp_user_id,
            detail={"response_count": len(response_evaluations)},
        )
    return attempt


def release_attempt_result(*, attempt_id: int, principal) -> QuizAttempt:
    """Professor releases a single evaluated attempt's result (UC-QZ-014)."""
    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().select_related("quiz").get(
            pk=attempt_id,
            quiz__created_by_user_id=principal.erp_user_id,
        )
        if attempt.status != AttemptStatus.EVALUATED:
            raise EvaluationError(
                "Only Evaluated attempts can be released."
            )
        attempt.status = AttemptStatus.RELEASED
        attempt.save(update_fields=["status"])

        QuizAuditLog.objects.create(
            quiz=attempt.quiz,
            attempt=attempt,
            action="result_released",
            actor_user_id=principal.erp_user_id,
        )
    return attempt


def release_all_results(*, quiz_id: int, principal) -> int:
    """Release all evaluated attempts for a quiz — returns count released."""
    with transaction.atomic():
        from modules.quiz.models import Quiz
        quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        updated = QuizAttempt.objects.filter(
            quiz=quiz, status=AttemptStatus.EVALUATED
        ).update(status=AttemptStatus.RELEASED)

        if updated:
            QuizAuditLog.objects.create(
                quiz=quiz,
                action="all_results_released",
                actor_user_id=principal.erp_user_id,
                detail={"count": updated},
            )
    return updated
