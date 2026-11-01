"""The professor's writes: quizzes, questions, publishing (CW-QZ-01).

Raises domain errors, never DRF exceptions, so it stays callable from a task.
The caller passes `scope`, a queryset of what this actor may touch.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.quizzes.domain import scoring
from modules.quizzes.domain import state_machine as sm
from modules.quizzes.models import Option, Question, Quiz

log = logging.getLogger("fusion.quizzes.authoring")


def _get(scope, pk: int, *, for_update: bool = False) -> Quiz:
    qs = scope.select_for_update() if for_update else scope
    quiz = qs.filter(pk=pk).first()
    if quiz is None:
        raise NotFoundError("No such quiz.")
    return quiz


def _require_editable(quiz: Quiz) -> None:
    if quiz.status not in sm.EDITABLE:
        raise ConflictError("A quiz cannot be changed once it is available.",
                            code="quiz_locked")          # BR-QZ-005


def _move(quiz: Quiz, to: str, actor_kind: str) -> None:
    try:
        sm.resolve("quiz", quiz.status, to, actor_kind)
    except (sm.InvalidTransition, sm.ActorNotAllowed) as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    log.info("quiz %s: %s -> %s by %s", quiz.pk, quiz.status, to, actor_kind)
    quiz.status = to


def create_quiz(*, owner_user_id: int, data: dict) -> Quiz:
    return Quiz.objects.create(owner_user_id=owner_user_id, status=sm.DRAFT, **data)


@transaction.atomic
def update_quiz(*, scope, pk: int, data: dict) -> Quiz:
    quiz = _get(scope, pk, for_update=True)
    _require_editable(quiz)
    for field, value in data.items():
        setattr(quiz, field, value)
    quiz.save()
    return quiz


def _create_question(*, quiz, owner_user_id: int, data: dict, position: int) -> Question:
    options = data.pop("options", [])
    question = Question.objects.create(quiz=quiz, owner_user_id=owner_user_id,
                                       position=position, **data)
    Option.objects.bulk_create(
        Option(question=question, position=i, **o) for i, o in enumerate(options))
    return question


@transaction.atomic
def add_question(*, scope, quiz_id: int, owner_user_id: int, data: dict) -> Question:
    quiz = _get(scope, quiz_id, for_update=True)
    _require_editable(quiz)
    data["course_code"] = data.get("course_code") or quiz.course_code
    return _create_question(quiz=quiz, owner_user_id=owner_user_id, data=data,
                            position=quiz.questions.count())


@transaction.atomic
def add_to_bank(*, owner_user_id: int, data: dict) -> Question:
    """UC-QZ-003. A bank question belongs to no quiz until it is copied in."""
    return _create_question(quiz=None, owner_user_id=owner_user_id, data=data,
                            position=0)


@transaction.atomic
def remove_question(*, scope, quiz_id: int, question_id: int) -> None:
    quiz = _get(scope, quiz_id, for_update=True)
    _require_editable(quiz)
    deleted, _ = quiz.questions.filter(pk=question_id).delete()
    if not deleted:
        raise NotFoundError("No such question on this quiz.")


@transaction.atomic
def copy_from_bank(*, scope, quiz_id: int, question_ids: list[int],
                   owner_user_id: int) -> list[Question]:
    """Bank questions are copied, not moved, so the bank stays reusable."""
    quiz = _get(scope, quiz_id, for_update=True)
    _require_editable(quiz)
    sources = list(Question.objects.filter(
        pk__in=question_ids, owner_user_id=owner_user_id, quiz__isnull=True)
        .prefetch_related("options"))
    if len(sources) != len(set(question_ids)):
        raise NotFoundError("One or more questions are not in your bank.")
    start = quiz.questions.count()
    copies = []
    for offset, src in enumerate(sources):
        options = list(src.options.all())
        src.pk, src.quiz, src.position = None, quiz, start + offset
        src.save()
        Option.objects.bulk_create(
            Option(question=src, text=o.text, is_correct=o.is_correct,
                   position=o.position) for o in options)
        copies.append(src)
    return copies


def _publish_problems(quiz: Quiz) -> list[str]:
    questions = list(quiz.questions.all())
    if not questions:
        return ["Add at least one question."]
    problems = []
    for n, q in enumerate(questions, start=1):
        problems += [f"Question {n}: {p}"
                     for p in scoring.validate_key(q.key(), len(q.options.all()))]
    if quiz.passing_marks > quiz.max_marks:
        problems.append("Passing marks exceed the quiz's maximum marks.")
    return problems


@transaction.atomic
def publish(*, scope, pk: int) -> Quiz:
    quiz = _get(scope, pk, for_update=True)
    problems = _publish_problems(quiz)
    if problems:
        raise BadRequestError("This quiz is not ready to publish.",
                              code="not_publishable", details={"problems": problems})
    _move(quiz, sm.publish_target(quiz.opens_at, timezone.now()), sm.PROFESSOR)
    quiz.save(update_fields=["status", "updated_at"])
    return quiz


@transaction.atomic
def close(*, scope, pk: int) -> Quiz:
    quiz = _get(scope, pk, for_update=True)
    _move(quiz, sm.CLOSED, sm.PROFESSOR)
    quiz.save(update_fields=["status", "updated_at"])
    return quiz


@transaction.atomic
def archive(*, scope, pk: int) -> Quiz:
    """Archive rather than delete once any attempt exists (BR-QZ-023)."""
    quiz = _get(scope, pk, for_update=True)
    _move(quiz, sm.ARCHIVED, sm.PROFESSOR)
    quiz.save(update_fields=["status", "updated_at"])
    return quiz


def apply_time_boundaries(now=None) -> dict[str, int]:
    """The system's moves: open scheduled quizzes, close expired ones."""
    now = now or timezone.now()
    opened = Quiz.objects.filter(status=sm.SCHEDULED, opens_at__lte=now) \
        .update(status=sm.AVAILABLE, updated_at=now)
    closed = Quiz.objects.filter(status=sm.AVAILABLE, closes_at__lte=now) \
        .update(status=sm.CLOSED, updated_at=now)
    return {"opened": opened, "closed": closed}
