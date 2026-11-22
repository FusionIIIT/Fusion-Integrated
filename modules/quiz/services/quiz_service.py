import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.quiz.domain.state_machine import M1, GuardFailed, IllegalTransition, apply_transition
from modules.quiz.models import AuditLogEntry, Notification, Quiz, QuizSettings


@transaction.atomic
def create_quiz(
    course_id: int,
    title: str,
    instructions: str,
    duration_minutes: int,
    max_attempts: int,
    created_by_user_id: int,
) -> Quiz:
    if duration_minutes <= 0:
        raise BadRequestError(
            "Quiz duration must be greater than zero minutes.", code="INVALID_DURATION"
        )
    if max_attempts <= 0:
        raise BadRequestError("Maximum attempts must be at least 1.", code="INVALID_MAX_ATTEMPTS")

    quiz = Quiz.objects.create(
        course_id=course_id,
        title=title,
        instructions=instructions,
        status="DRAFT",
        created_by_user_id=created_by_user_id,
        duration_minutes=duration_minutes,
        max_attempts=max_attempts,
    )
    QuizSettings.objects.create(quiz=quiz)
    AuditLogEntry.objects.create(
        quiz_id=quiz.pk, event="QUIZ_CREATED", actor_user_id=created_by_user_id
    )
    return quiz


@transaction.atomic
def update_quiz(quiz_id: int, user_id: int, **kwargs) -> Quiz:
    quiz = Quiz.objects.select_for_update().get(pk=quiz_id)
    if quiz.created_by_user_id != user_id:
        raise PermissionDeniedError(
            "You can only modify quizzes for your own courses.", code="NOT_COURSE_OWNER"
        )
    if quiz.status not in ("DRAFT", "DRAFT_CONFIGURED", "READY_TO_PUBLISH"):
        raise ConflictError(
            "Quizzes cannot be edited after publication.", code="QUIZ_ALREADY_ACTIVE"
        )

    for key, val in kwargs.items():
        if hasattr(quiz, key) and val is not None:
            setattr(quiz, key, val)
    quiz.save()
    AuditLogEntry.objects.create(quiz_id=quiz.pk, event="QUIZ_UPDATED", actor_user_id=user_id)
    return quiz


@transaction.atomic
def publish_quiz(
    quiz_id: int,
    user_id: int,
    start_at: datetime.datetime | None = None,
    close_at: datetime.datetime | None = None,
) -> Quiz:
    quiz = Quiz.objects.select_for_update().get(pk=quiz_id)
    if quiz.created_by_user_id != user_id:
        raise PermissionDeniedError(
            "You can only publish quizzes for your own courses.", code="NOT_COURSE_OWNER"
        )

    now = timezone.now()
    if start_at:
        quiz.start_at = start_at
    if close_at:
        quiz.close_at = close_at

    ctx = {
        "owns_course": True,
        "questions_valid": quiz.questions.exists(),
        "config_valid": hasattr(quiz, "settings"),
        "start_at": quiz.start_at,
        "close_at": quiz.close_at,
        "now": now,
    }

    # Run through transitions
    if quiz.status == "DRAFT":
        quiz.status = apply_transition(M1, quiz.status, "configure", "PROFESSOR", ctx)
    if quiz.status == "DRAFT_CONFIGURED":
        quiz.status = apply_transition(M1, quiz.status, "prepare", "PROFESSOR", ctx)
    try:
        quiz.status = apply_transition(M1, quiz.status, "publish", "PROFESSOR", ctx)
    except (GuardFailed, IllegalTransition) as e:
        raise ConflictError(f"Quiz cannot be published: {e!s}", code="PUBLISH_FAILED") from e

    quiz.save()
    AuditLogEntry.objects.create(quiz_id=quiz.pk, event="QUIZ_PUBLISHED", actor_user_id=user_id)
    Notification.objects.create(
        recipient_user_id=user_id, event="QUIZ_PUBLISHED", payload={"quiz_id": quiz.pk}
    )
    return quiz


@transaction.atomic
def archive_quiz(quiz_id: int, user_id: int) -> Quiz:
    quiz = Quiz.objects.select_for_update().get(pk=quiz_id)
    if quiz.created_by_user_id != user_id:
        raise PermissionDeniedError(
            "You can only archive quizzes for your own courses.", code="NOT_COURSE_OWNER"
        )

    ctx = {
        "archive_permitted": not quiz.attempts.filter(status="STARTED").exists(),
        "now": timezone.now(),
    }
    try:
        quiz.status = apply_transition(M1, quiz.status, "archive", "PROFESSOR", ctx)
    except (GuardFailed, IllegalTransition) as e:
        raise ConflictError(f"Cannot archive quiz: {e!s}", code="ARCHIVE_FAILED") from e

    quiz.save()
    AuditLogEntry.objects.create(quiz_id=quiz.pk, event="QUIZ_ARCHIVED", actor_user_id=user_id)
    return quiz
