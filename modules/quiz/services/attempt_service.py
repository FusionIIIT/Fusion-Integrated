import datetime
import random
import uuid

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.quiz.domain.rules import can_attempt_quiz
from modules.quiz.models import (
    AttemptResponse,
    AuditLogEntry,
    Notification,
    Quiz,
    QuizAttempt,
)


@transaction.atomic
def start_quiz_attempt(quiz_id: int, student_id: int) -> QuizAttempt:
    quiz = Quiz.objects.select_related("settings").prefetch_related("questions").get(pk=quiz_id)
    now = timezone.now()

    # Check if student already has active attempt
    active = QuizAttempt.objects.filter(quiz=quiz, student_id=student_id, status="STARTED").first()
    if active:
        return active

    attempts_count = QuizAttempt.objects.filter(quiz=quiz, student_id=student_id).count()
    allowed, reason = can_attempt_quiz(quiz, attempts_count, now=now)
    if not allowed:
        raise ConflictError(reason, code="ATTEMPT_NOT_ALLOWED")

    # Generate seed and deterministic question ordering
    seed = uuid.uuid4().hex
    question_ids = list(quiz.questions.values_list("id", flat=True))
    random.Random(seed).shuffle(question_ids)  # noqa: S311

    deadline_at = now + datetime.timedelta(minutes=quiz.duration_minutes)
    if quiz.close_at and quiz.close_at < deadline_at:
        deadline_at = quiz.close_at

    attempt = QuizAttempt.objects.create(
        quiz=quiz,
        student_id=student_id,
        status="STARTED",
        deadline_at=deadline_at,
        seed=seed,
        question_order=question_ids,
        tab_violations=0,
    )
    AuditLogEntry.objects.create(quiz_id=quiz.pk, event="ATTEMPT_STARTED", actor_user_id=student_id)
    return attempt


@transaction.atomic
def save_response(attempt_id: int, student_id: int, question_id: int, answer) -> AttemptResponse:
    attempt = (
        QuizAttempt.objects.select_for_update().select_related("quiz__settings").get(pk=attempt_id)
    )
    if attempt.student_id != student_id:
        raise PermissionDeniedError(
            "You can only modify your own attempt.", code="NOT_ATTEMPT_OWNER"
        )
    if attempt.status != "STARTED":
        raise ConflictError(
            "This attempt has already been submitted and cannot be changed.",
            code="ATTEMPT_SUBMITTED",
        )
    if timezone.now() > attempt.deadline_at:
        submit_quiz_attempt(attempt_id, student_id)
        raise ConflictError(
            "Attempt deadline has expired. The quiz has been auto-submitted.",
            code="ATTEMPT_EXPIRED",
        )

    resp, _ = AttemptResponse.objects.update_or_create(
        attempt=attempt,
        question_id=question_id,
        defaults={"answer": answer},
    )
    return resp


@transaction.atomic
def record_tab_violation(attempt_id: int, student_id: int) -> dict:
    attempt = (
        QuizAttempt.objects.select_for_update().select_related("quiz__settings").get(pk=attempt_id)
    )
    if attempt.student_id != student_id:
        raise PermissionDeniedError("Forbidden", code="NOT_OWNER")
    if attempt.status != "STARTED":
        return {"status": attempt.status, "tab_violations": attempt.tab_violations}

    attempt.tab_violations += 1
    limit = getattr(attempt.quiz.settings, "tab_violation_limit", 3)
    if attempt.tab_violations >= limit:
        attempt.status = "SUBMITTED"
        attempt.submitted_at = timezone.now()
        attempt.save()
        from modules.quiz.services.evaluation_service import auto_evaluate_objective_responses

        auto_evaluate_objective_responses(attempt.pk)
        AuditLogEntry.objects.create(
            quiz_id=attempt.quiz_id,
            event="ATTEMPT_AUTO_SUBMITTED_VIOLATION",
            actor_user_id=student_id,
        )
        return {
            "status": "SUBMITTED",
            "tab_violations": attempt.tab_violations,
            "reason": "VIOLATION_LIMIT_REACHED",
        }

    attempt.save()
    return {"status": "STARTED", "tab_violations": attempt.tab_violations}


@transaction.atomic
def submit_quiz_attempt(attempt_id: int, student_id: int) -> QuizAttempt:
    attempt = (
        QuizAttempt.objects.select_for_update().select_related("quiz__settings").get(pk=attempt_id)
    )
    if attempt.student_id != student_id:
        raise PermissionDeniedError(
            "You can only submit your own attempt.", code="NOT_ATTEMPT_OWNER"
        )
    if attempt.status == "SUBMITTED":
        return attempt

    # Check unanswered question setting
    settings = getattr(attempt.quiz, "settings", None)
    if settings and not settings.allow_unanswered:
        total_questions = attempt.quiz.questions.count()
        answered = attempt.responses.exclude(answer__isnull=True).exclude(answer="").count()
        if answered < total_questions:
            raise BadRequestError(
                "All questions must be answered before submission.", code="UNANSWERED_NOT_PERMITTED"
            )

    attempt.status = "SUBMITTED"
    attempt.submitted_at = timezone.now()
    attempt.save()

    from modules.quiz.services.evaluation_service import auto_evaluate_objective_responses

    auto_evaluate_objective_responses(attempt.pk)

    AuditLogEntry.objects.create(
        quiz_id=attempt.quiz_id, event="ATTEMPT_SUBMITTED", actor_user_id=student_id
    )
    Notification.objects.create(
        recipient_user_id=student_id, event="ATTEMPT_SUBMITTED", payload={"attempt_id": attempt.pk}
    )
    return attempt


@transaction.atomic
def auto_submit_expired_attempts():
    now = timezone.now()
    expired = QuizAttempt.objects.filter(status="STARTED", deadline_at__lte=now)
    for attempt in expired:
        attempt.status = "SUBMITTED"
        attempt.submitted_at = now
        attempt.save()
        from modules.quiz.services.evaluation_service import auto_evaluate_objective_responses

        auto_evaluate_objective_responses(attempt.pk)
        AuditLogEntry.objects.create(
            quiz_id=attempt.quiz_id,
            event="ATTEMPT_AUTO_SUBMITTED_TIME",
            actor_user_id=attempt.student_id,
        )
