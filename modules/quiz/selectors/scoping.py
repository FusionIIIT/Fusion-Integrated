"""Read-only Quiz query builders with caller-supplied scope facts.

These selectors do not resolve IAM permissions, course associations, or
academic eligibility. Callers must supply those verified scalar scopes.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import Count, Prefetch, Q, QuerySet

from modules.quiz.models import (
    Attempt,
    AttemptQuestion,
    Question,
    QuestionOption,
    Quiz,
    QuizResult,
)


def quizzes_for_courses(course_ids: Iterable[int]) -> QuerySet[Quiz]:
    """Return quizzes only from the caller's already-authorized course scope."""

    return Quiz.objects.filter(course_id__in=course_ids).order_by("start_at", "pk")


def quiz_for_courses(*, public_id: UUID, course_ids: Iterable[int]) -> QuerySet[Quiz]:
    """Return a course-scoped Quiz detail queryset; an out-of-scope ID is absent."""

    return quizzes_for_courses(course_ids).filter(public_id=public_id)


def _eligible_quiz_rows(
    *, eligible_quiz_ids: Iterable[UUID], student_user_id: int, server_now: datetime
) -> QuerySet[Quiz]:
    """Filter to supplied eligibility facts and current/upcoming lifecycle windows."""

    visible_window = Q(status="available", start_at__lte=server_now, close_at__gt=server_now)
    visible_window |= Q(status="scheduled", start_at__isnull=False, close_at__gt=server_now)
    return (
        Quiz.objects.filter(public_id__in=eligible_quiz_ids)
        .filter(visible_window)
        .annotate(
            question_count=Count("quiz_questions", distinct=True),
            attempts_started=Count(
                "attempts",
                filter=Q(attempts__student_user_id=student_user_id),
                distinct=True,
            ),
        )
    )


def eligible_quizzes_for_student(
    *, eligible_quiz_ids: Iterable[UUID], student_user_id: int, server_now: datetime
) -> QuerySet[Quiz]:
    """Return supplied eligible quizzes that are available now or scheduled next."""

    return _eligible_quiz_rows(
        eligible_quiz_ids=eligible_quiz_ids,
        student_user_id=student_user_id,
        server_now=server_now,
    ).order_by("start_at", "pk")


def quiz_prestart_for_student(
    *,
    public_id: UUID,
    eligible_quiz_ids: Iterable[UUID],
    student_user_id: int,
    server_now: datetime,
) -> QuerySet[Quiz]:
    """Return one pre-start Quiz only when its public ID is in the supplied scope."""

    return eligible_quizzes_for_student(
        eligible_quiz_ids=eligible_quiz_ids,
        student_user_id=student_user_id,
        server_now=server_now,
    ).filter(public_id=public_id)


def attempts_for_student(student_user_id: int) -> QuerySet[Attempt]:
    """Return a Student's own attempts with their Quiz loaded in one query."""

    return (
        Attempt.objects.filter(student_user_id=student_user_id)
        .select_related("quiz")
        .order_by("-started_at", "-pk")
    )


def attempt_for_student(*, attempt_id: int, student_user_id: int) -> QuerySet[Attempt]:
    """Return one Student-owned attempt or an empty queryset."""

    return attempts_for_student(student_user_id).filter(pk=attempt_id)


def attempts_for_courses(course_ids: Iterable[int]) -> QuerySet[Attempt]:
    """Return attempts whose Quiz belongs to the caller's authorized courses."""

    return (
        Attempt.objects.filter(quiz__course_id__in=course_ids)
        .select_related("quiz")
        .order_by("-started_at", "-pk")
    )


def student_attempt_presentation_rows(
    *, attempt_id: int, student_user_id: int
) -> QuerySet[dict[str, Any]]:
    """Return flat rows grouped by item ID, with stored option order as authority.

    Each attempt-question has one row per option, or one row with null option
    fields when it has none. Group by ``id``; reorder option rows using the
    repeated ``displayed_option_keys`` list, matching its entries to canonical
    ``question__options__option_key`` values. The database order of option rows
    is stable by canonical ID and is not the randomized presentation order.
    Missing Response rows have null response fields. Correctness and answer-key
    data are deliberately absent.
    """

    return (
        AttemptQuestion.objects.filter(
            attempt_id=attempt_id,
            attempt__student_user_id=student_user_id,
        )
        .order_by("display_order", "pk", "question__options__option_key")
        .values(
            "id",
            "display_order",
            "marks_at_start",
            "displayed_option_keys",
            "question__public_id",
            "question__question_type",
            "question__prompt",
            "question__options__option_key",
            "question__options__text",
            "response__answer_payload",
            "response__revision",
            "response__saved_at",
        )
    )


def student_result_rows(
    *, student_user_id: int, result_id: int | None = None
) -> QuerySet[dict[str, Any]]:
    """Project only released result fields belonging to the authenticated Student."""

    results = QuizResult.objects.filter(
        attempt__student_user_id=student_user_id,
        status="released",
    )
    if result_id is not None:
        results = results.filter(pk=result_id)
    return results.values(
        "id",
        "status",
        "total_marks",
        "marks_obtained",
        "percentage",
        "correct_count",
        "incorrect_count",
        "unanswered_count",
        "passed",
        "released_at",
        "attempt__attempt_number",
        "attempt__started_at",
        "attempt__submitted_at",
        "attempt__quiz__public_id",
        "attempt__quiz__title",
    ).order_by("-released_at", "-pk")


def released_results_for_student(student_user_id: int) -> QuerySet[dict[str, Any]]:
    """Return the Student's released score/history projection only."""

    return student_result_rows(student_user_id=student_user_id)


def results_for_courses(course_ids: Iterable[int]) -> QuerySet[QuizResult]:
    """Return Professor-side result rows scoped to the caller's authorized courses."""

    return (
        QuizResult.objects.filter(attempt__quiz__course_id__in=course_ids)
        .select_related("attempt", "attempt__quiz")
        .order_by("-created_at", "-pk")
    )


def question_bank_for_creator(
    *,
    creator_user_id: int,
    subject_id: int | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
    question_type: str | None = None,
) -> QuerySet[Question]:
    """Return the caller-owned Question Bank subset with options prefetched.

    Creator-only scope is a conservative provisional boundary. Whether the
    Question Bank is shared across Professors, and how that access is granted,
    remains unresolved; this selector does not establish an institutional rule.
    """

    questions = Question.objects.filter(created_by_user_id=creator_user_id)
    if subject_id is not None:
        questions = questions.filter(subject_id=subject_id)
    if topic:
        questions = questions.filter(topic__icontains=topic)
    if difficulty:
        questions = questions.filter(difficulty=difficulty)
    if question_type:
        questions = questions.filter(question_type=question_type)
    option_rows = QuestionOption.objects.order_by("position", "pk")
    return questions.prefetch_related(Prefetch("options", queryset=option_rows)).order_by(
        "topic", "pk"
    )
