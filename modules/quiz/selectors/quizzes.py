"""Quiz selectors — read-only queries, ownership/scope filtering here."""
from __future__ import annotations

from django.db import models
from django.db.models import Count, OuterRef, QuerySet, Subquery
from django.utils import timezone

from modules.quiz.domain.state_machine import AttemptStatus, QuizStatus
from modules.quiz.models import Quiz, QuizAttempt


def quizzes_for_professor(principal) -> QuerySet[Quiz]:
    """All quizzes created by this professor, annotated with question/attempt counts."""
    return (
        Quiz.objects.filter(created_by_user_id=principal.erp_user_id)
        .annotate(
            question_count=Count("questions", distinct=True),
            attempt_count=Count("attempts", distinct=True),
        )
        .order_by("-created_at")
    )


def quiz_detail_for_professor(quiz_id: int, principal) -> Quiz:
    """Single quiz — 404 if not owned by this professor."""
    return (
        Quiz.objects.annotate(
            question_count=Count("questions", distinct=True),
            attempt_count=Count("attempts", distinct=True),
        )
        .get(pk=quiz_id, created_by_user_id=principal.erp_user_id)
    )


def eligible_quizzes_for_student(principal) -> QuerySet[Quiz]:
    """Available quizzes the student hasn't exhausted all attempts on."""
    now = timezone.now()
    user_id = principal.erp_user_id

    # Count completed (submitted+) attempts this student has for each quiz
    student_attempts_subq = (
        QuizAttempt.objects.filter(
            quiz=OuterRef("pk"),
            user_id=user_id,
        )
        .exclude(status=AttemptStatus.IN_PROGRESS)
        .values("quiz")
        .annotate(n=Count("pk"))
        .values("n")
    )

    return (
        Quiz.objects.filter(status=QuizStatus.AVAILABLE)
        .filter(
            models.Q(start_at__isnull=True) | models.Q(start_at__lte=now)
        )
        .filter(
            models.Q(close_at__isnull=True) | models.Q(close_at__gt=now)
        )
        .annotate(
            student_attempt_count=Subquery(
                student_attempts_subq[:1], output_field=models.IntegerField()
            ),
            question_count=Count("questions", distinct=True),
        )
        .filter(
            # student_attempt_count is NULL when no attempts exist — that's fine too
            models.Q(student_attempt_count__isnull=True)
            | models.Q(student_attempt_count__lt=models.F("max_attempts"))
        )
        .order_by("close_at", "title")
    )


def all_eligible_quizzes_for_student(principal) -> QuerySet[Quiz]:
    """Available + upcoming quizzes visible to student (for dashboard)."""
    user_id = principal.erp_user_id

    student_attempts_subq = (
        QuizAttempt.objects.filter(
            quiz=OuterRef("pk"),
            user_id=user_id,
        )
        .exclude(status=AttemptStatus.IN_PROGRESS)
        .values("quiz")
        .annotate(n=Count("pk"))
        .values("n")
    )

    return (
        Quiz.objects.filter(
            status__in=[QuizStatus.AVAILABLE, QuizStatus.SCHEDULED]
        )
        .annotate(
            student_attempt_count=Subquery(
                student_attempts_subq[:1], output_field=models.IntegerField()
            ),
            question_count=Count("questions", distinct=True),
        )
        .order_by("close_at", "start_at", "title")
    )


# Fix missing import
