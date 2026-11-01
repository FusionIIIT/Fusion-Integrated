"""All writes: authoring (CW-QZ-01), attempts (CW-QZ-02), results (CW-QZ-03).

Raises domain errors, never DRF exceptions, so it stays callable from a task.
The caller passes `scope`, a queryset of what this actor may touch.
"""
from __future__ import annotations

import random

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.quizzes.domain import scoring
from modules.quizzes.domain import state_machine as sm
from modules.quizzes.models import Attempt, Option, Question, Quiz


def _get(qs, pk: int, what: str):
    obj = qs.select_for_update(of=("self",)).filter(pk=pk).first()
    if obj is None:
        raise NotFoundError(f"No such {what}.")
    return obj


def _move(kind: str, obj, to: str, actor: str) -> None:
    try:
        sm.check(kind, obj.status, to, actor)
    except sm.InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    obj.status = to


# -- authoring ---------------------------------------------------------------

@transaction.atomic
def create_quiz(*, owner_user_id: int, data: dict) -> Quiz:
    """A quiz and its questions arrive together, as a draft."""
    questions = data.pop("questions", [])
    quiz = Quiz.objects.create(owner_user_id=owner_user_id, **data)
    for position, q in enumerate(questions):
        options = q.pop("options", [])
        question = Question.objects.create(quiz=quiz, position=position, **q)
        Option.objects.bulk_create(Option(question=question, **o) for o in options)
    return quiz


@transaction.atomic
def publish(*, scope, quiz_id: int) -> Quiz:
    quiz = _get(scope, quiz_id, "quiz")
    questions = list(quiz.questions.prefetch_related("options"))
    problems = [] if questions else ["Add at least one question."]
    for n, q in enumerate(questions, start=1):
        problems += [f"Question {n}: {p}"
                     for p in scoring.validate_key(q.key(), len(q.options.all()))]
    if problems:
        raise BadRequestError("This quiz is not ready to publish.",
                              code="not_publishable", details={"problems": problems})
    _move("quiz", quiz, sm.publish_target(quiz.opens_at, timezone.now()), sm.PROFESSOR)
    quiz.save(update_fields=["status", "updated_at"])
    return quiz


# -- attempts ----------------------------------------------------------------

@transaction.atomic
def start_attempt(*, quiz_id: int, student_user_id: int) -> Attempt:
    now = timezone.now()
    quiz = _get(Quiz.objects.exclude(status=sm.DRAFT), quiz_id, "quiz")
    if not sm.is_open(quiz.status, quiz.opens_at, quiz.closes_at, now):
        raise ConflictError("This quiz is not open.", code="quiz_not_open")
    previous = quiz.attempts.filter(student_user_id=student_user_id)
    if previous.filter(status=sm.IN_PROGRESS).exists():
        raise ConflictError("Finish your current attempt first.",
                            code="attempt_in_progress")
    if previous.count() >= quiz.max_attempts:                      # BR-QZ-008
        raise ConflictError("No attempts left.", code="attempts_exhausted")
    order = list(quiz.questions.values_list("id", flat=True))
    if quiz.shuffle_questions:
        random.shuffle(order)
    return Attempt.objects.create(
        quiz=quiz, student_user_id=student_user_id, question_order=order,
        deadline=sm.attempt_deadline(now, quiz.duration_minutes, quiz.closes_at))


@transaction.atomic
def save_response(*, scope, attempt_id: int, question_id: int,
                  selected_option_ids: list[int], text: str) -> None:
    attempt = _get(scope, attempt_id, "attempt")
    if attempt.status != sm.IN_PROGRESS or timezone.now() >= attempt.deadline:
        raise ConflictError("This attempt is closed.", code="attempt_closed")
    if question_id not in attempt.question_order:
        raise NotFoundError("That question is not part of this attempt.")
    valid = set(Option.objects.filter(question_id=question_id)
                .values_list("id", flat=True))
    if not set(selected_option_ids) <= valid:
        raise BadRequestError("Unknown option for this question.")
    attempt.answers[str(question_id)] = {"options": sorted(set(selected_option_ids)),
                                         "text": text}
    attempt.save(update_fields=["answers", "updated_at"])


def _finish(attempt: Attempt, to: str, actor: str) -> Attempt:
    """Submits and marks in one step: every question type is objective."""
    _move("attempt", attempt, to, actor)
    attempt.score = scoring.total(                                 # BR-QZ-020
        scoring.mark(q.key(), attempt.answer(q.id), attempt.quiz.negative_marking)
        for q in attempt.quiz.questions.prefetch_related("options"))
    attempt.save(update_fields=["status", "score", "updated_at"])
    return attempt


@transaction.atomic
def submit_attempt(*, scope, attempt_id: int) -> Attempt:
    return _finish(_get(scope, attempt_id, "attempt"), sm.SUBMITTED, sm.STUDENT)


def apply_time_boundaries(now=None) -> dict[str, int]:
    """The system's moves: open and close quizzes, auto-submit expired attempts."""
    now = now or timezone.now()
    opened = Quiz.objects.filter(status=sm.SCHEDULED, opens_at__lte=now) \
        .update(status=sm.AVAILABLE, updated_at=now)
    closed = Quiz.objects.filter(status=sm.AVAILABLE, closes_at__lte=now) \
        .update(status=sm.CLOSED, updated_at=now)
    expired = Attempt.objects.filter(status=sm.IN_PROGRESS, deadline__lte=now)
    submitted = 0
    for pk in expired.values_list("pk", flat=True):
        with transaction.atomic():
            attempt = _get(Attempt.objects.filter(status=sm.IN_PROGRESS), pk, "attempt")
            _finish(attempt, sm.AUTO_SUBMITTED, sm.SYSTEM)          # BR-QZ-017
            submitted += 1
    return {"opened": opened, "closed": closed, "auto_submitted": submitted}
