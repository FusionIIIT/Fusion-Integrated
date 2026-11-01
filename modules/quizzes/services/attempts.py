"""Attempts, evaluation and release (CW-QZ-02, CW-QZ-03)."""
from __future__ import annotations

import logging
import random
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.quizzes.domain import scoring
from modules.quizzes.domain import state_machine as sm
from modules.quizzes.models import Attempt, Quiz, Response
from modules.quizzes.selectors import quizzes as selectors

log = logging.getLogger("fusion.quizzes.attempts")


def _move(attempt: Attempt, to: str, actor_kind: str) -> None:
    try:
        sm.resolve("attempt", attempt.status, to, actor_kind)
    except (sm.InvalidTransition, sm.ActorNotAllowed) as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    attempt.status = to


def _own_attempt(student_user_id: int, pk: int, *, for_update=False) -> Attempt:
    qs = selectors.attempts_of(student_user_id)
    attempt = (qs.select_for_update(of=("self",)) if for_update else qs) \
        .filter(pk=pk).first()
    if attempt is None:
        raise NotFoundError("No such attempt.")
    return attempt


@transaction.atomic
def start(*, quiz_id: int, student_user_id: int) -> Attempt:
    now = timezone.now()
    quiz = Quiz.objects.select_for_update().filter(pk=quiz_id).first()
    if quiz is None or quiz.status not in (sm.SCHEDULED, sm.AVAILABLE, sm.CLOSED):
        raise NotFoundError("No such quiz.")
    if not sm.is_open(quiz.status, quiz.opens_at, quiz.closes_at, now):
        raise ConflictError("This quiz is not open.", code="quiz_not_open")

    previous = quiz.attempts.filter(student_user_id=student_user_id)
    if previous.filter(status=sm.IN_PROGRESS).exists():
        raise ConflictError("Finish your current attempt first.",
                            code="attempt_in_progress")
    used = previous.count()
    if used >= quiz.max_attempts:
        raise ConflictError("No attempts left.", code="attempts_exhausted")  # BR-QZ-008

    order = list(quiz.questions.values_list("id", flat=True))
    if quiz.shuffle_questions:
        random.shuffle(order)
    return Attempt.objects.create(
        quiz=quiz, student_user_id=student_user_id, number=used + 1,
        started_at=now, question_order=order,
        deadline=sm.attempt_deadline(now, quiz.duration_minutes, quiz.closes_at))


@transaction.atomic
def save_response(*, attempt_id: int, student_user_id: int, question_id: int,
                  selected_option_ids: list[int], text: str) -> Response:
    """Saved as the student goes, so a dropped connection loses nothing (BR-QZ-015)."""
    attempt = _own_attempt(student_user_id, attempt_id, for_update=True)
    if attempt.status != sm.IN_PROGRESS:
        raise ConflictError("A submitted attempt cannot change.",
                            code="attempt_closed")          # BR-QZ-016
    if timezone.now() >= attempt.deadline:
        raise ConflictError("Time is up.", code="attempt_expired")
    if question_id not in attempt.question_order:
        raise NotFoundError("That question is not part of this attempt.")
    valid = set(attempt.quiz.questions.get(pk=question_id)
                .options.values_list("id", flat=True))
    if not set(selected_option_ids) <= valid:
        raise BadRequestError("Unknown option for this question.")
    response, _ = Response.objects.update_or_create(
        attempt=attempt, question_id=question_id,
        defaults={"selected_option_ids": sorted(set(selected_option_ids)),
                  "text": text})
    return response


def _finish(attempt: Attempt, to: str, actor_kind: str) -> Attempt:
    _move(attempt, to, actor_kind)
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["status", "submitted_at", "updated_at"])
    evaluate_objective(attempt)
    return attempt


@transaction.atomic
def submit(*, attempt_id: int, student_user_id: int) -> Attempt:
    attempt = _own_attempt(student_user_id, attempt_id, for_update=True)
    if not attempt.quiz.allow_unanswered:                    # BR-QZ-012
        answered = {r.question_id for r in attempt.responses.all()
                    if not r.answer().is_blank}
        missing = len(set(attempt.question_order) - answered)
        if missing:
            raise BadRequestError(f"{missing} question(s) are unanswered.",
                                  code="unanswered_questions")
    return _finish(attempt, sm.SUBMITTED, sm.STUDENT)


def auto_submit_expired(now=None) -> int:
    """UC-QZ-011. Each attempt in its own transaction, so one bad row cannot
    hold the rest open past their deadline."""
    count = 0
    for pk in selectors.expired_attempts(now or timezone.now()) \
            .values_list("pk", flat=True):
        with transaction.atomic():
            attempt = Attempt.objects.select_for_update().get(pk=pk)
            if attempt.status == sm.IN_PROGRESS:
                _finish(attempt, sm.AUTO_SUBMITTED, sm.SYSTEM)
                count += 1
    return count


def evaluate_objective(attempt: Attempt) -> None:
    """UC-QZ-012. Marks every objective response; if nothing subjective is
    left, the attempt is fully evaluated."""
    questions = {q.id: q for q in attempt.quiz.questions.prefetch_related("options")}
    responses = {r.question_id: r for r in attempt.responses.all()}
    for qid in attempt.question_order:
        question = questions.get(qid)
        if question is None or not question.is_objective:
            continue
        response = responses.get(qid) or Response(attempt=attempt, question=question)
        response.awarded_marks = scoring.mark(
            question.key(), response.answer(), attempt.quiz.negative_marking)
        response.save()
    _maybe_complete(attempt, sm.SYSTEM)


def _maybe_complete(attempt: Attempt, actor_kind: str) -> None:
    graded = dict(attempt.responses.filter(awarded_marks__isnull=False)
                  .values_list("question_id", "awarded_marks"))
    subjective = set(attempt.quiz.questions.exclude(
        question_type__in=scoring.OBJECTIVE).values_list("id", flat=True))
    if (subjective & set(attempt.question_order)) - graded.keys():
        return                                  # still waiting on the professor
    attempt.score = scoring.total(graded.values())                     # BR-QZ-020
    _move(attempt, sm.EVALUATED, actor_kind)
    attempt.save(update_fields=["score", "status", "updated_at"])


@transaction.atomic
def grade_response(*, scope, attempt_id: int, question_id: int,
                   marks: Decimal, feedback: str = "") -> Attempt:
    """UC-QZ-013. The professor's mark is final; any AI suggestion is only
    advisory and never written here (BR-QZ-019)."""
    attempt = scope.select_for_update(of=("self",)).filter(pk=attempt_id).first()
    if attempt is None:
        raise NotFoundError("No such attempt.")
    if attempt.status not in (sm.SUBMITTED, sm.AUTO_SUBMITTED):
        raise ConflictError("Only a submitted, unevaluated attempt can be graded.",
                            code="not_gradable")
    question = attempt.quiz.questions.filter(pk=question_id).first()
    if question is None or question.is_objective:
        raise NotFoundError("No such subjective question on this quiz.")
    if not scoring.ZERO <= marks <= question.marks:
        raise BadRequestError(f"Marks must be between 0 and {question.marks}.")
    Response.objects.update_or_create(
        attempt=attempt, question=question,
        defaults={"awarded_marks": marks, "feedback": feedback})
    _maybe_complete(attempt, sm.PROFESSOR)
    return attempt


@transaction.atomic
def release(*, scope, quiz_id: int) -> int:
    """UC-QZ-014. Releases every evaluated attempt on the quiz at once."""
    attempts = list(scope.select_for_update(of=("self",))
                    .filter(quiz_id=quiz_id, status=sm.EVALUATED))
    for attempt in attempts:
        _move(attempt, sm.RELEASED, sm.PROFESSOR)
        attempt.save(update_fields=["status", "updated_at"])
    log.info("quiz %s: released %d results", quiz_id, len(attempts))
    return len(attempts)
