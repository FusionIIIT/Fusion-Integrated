from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.quiz.domain.scoring import NotObjective, compute_result, score_response
from modules.quiz.models import (
    AuditLogEntry,
    Notification,
    Quiz,
    QuizAttempt,
    QuizResult,
    ResponseEvaluation,
)


@transaction.atomic
def auto_evaluate_objective_responses(attempt_id: int) -> QuizResult:
    attempt = (
        QuizAttempt.objects.select_for_update()
        .select_related("quiz__settings")
        .prefetch_related("quiz__questions", "responses")
        .get(pk=attempt_id)
    )
    questions_by_id = {q.pk: q for q in attempt.quiz.questions.all()}
    responses_by_qid = {r.question_id: r for r in attempt.responses.all()}

    negative_enabled = getattr(attempt.quiz.settings, "negative_marking_enabled", False)
    scores = []
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0
    has_subjective = False

    for qid, q in questions_by_id.items():
        resp = responses_by_qid.get(qid)
        ans = resp.answer if resp else None

        if q.question_type in ["SHORT", "LONG"]:
            has_subjective = True
            if resp:
                ResponseEvaluation.objects.update_or_create(
                    response=resp, defaults={"status": "PENDING"}
                )
            continue

        q_dict = {
            "type": q.question_type,
            "marks": q.marks,
            "negative_marks": q.negative_marks,
            "correct": q.correct,
        }
        try:
            score = score_response(q_dict, ans, negative_enabled)
        except NotObjective:
            score = Decimal("0.00")

        scores.append(score)
        if ans is None or ans == "":
            unanswered_count += 1
        elif score > Decimal("0.00"):
            correct_count += 1
        else:
            incorrect_count += 1

        if resp:
            ResponseEvaluation.objects.update_or_create(
                response=resp,
                defaults={"status": "FINAL", "auto_marks": score, "final_marks": score},
            )

    total_max = sum(q.marks for q in questions_by_id.values())
    res_data = compute_result(
        scores=scores,
        max_marks=total_max,
        passing_marks=total_max * Decimal("0.4"),  # standard 40%
        counts={
            "correct": correct_count,
            "incorrect": incorrect_count,
            "unanswered": unanswered_count,
        },
    )

    status = "PARTIALLY_EVALUATED" if has_subjective else "EVALUATED"
    result, _ = QuizResult.objects.update_or_create(
        attempt=attempt,
        defaults={
            "status": status,
            "marks_obtained": res_data["marks_obtained"],
            "percentage": res_data["percentage"],
            "passed": res_data["passed"],
        },
    )
    AuditLogEntry.objects.create(
        quiz_id=attempt.quiz_id, event="ATTEMPT_EVALUATED", actor_user_id=attempt.student_id
    )
    return result


@transaction.atomic
def grade_subjective_response(
    evaluation_id: int, faculty_user_id: int, marks: Decimal, feedback: str = ""
) -> ResponseEvaluation:
    evaluation = (
        ResponseEvaluation.objects.select_for_update()
        .select_related("response__attempt__quiz")
        .get(pk=evaluation_id)
    )
    quiz = evaluation.response.attempt.quiz
    if quiz.created_by_user_id != faculty_user_id:
        raise PermissionDeniedError(
            "You can only grade responses for your own quizzes.", code="NOT_COURSE_OWNER"
        )

    max_q_marks = evaluation.response.question.marks
    if marks < Decimal("0.00") or marks > max_q_marks:
        raise BadRequestError(f"Marks must be between 0 and {max_q_marks}.", code="INVALID_MARKS")

    evaluation.final_marks = marks
    evaluation.feedback = feedback
    evaluation.finalized_by = faculty_user_id
    evaluation.status = "FINAL"
    evaluation.save()

    # Check if all responses are evaluated now
    attempt = evaluation.response.attempt
    pending = ResponseEvaluation.objects.filter(
        response__attempt=attempt, status__in=["PENDING", "AI_SUGGESTED"]
    ).exists()
    if not pending:
        # Recompute total
        all_evals = ResponseEvaluation.objects.filter(response__attempt=attempt)
        total_obtained = sum((e.final_marks or Decimal(0)) for e in all_evals)
        total_max = sum(q.marks for q in quiz.questions.all())
        pct = (total_obtained * Decimal(100) / total_max) if total_max else Decimal(0)
        QuizResult.objects.update_or_create(
            attempt=attempt,
            defaults={
                "status": "EVALUATED",
                "marks_obtained": total_obtained,
                "percentage": pct,
                "passed": pct >= Decimal(40),
            },
        )
    return evaluation


@transaction.atomic
def release_quiz_results(quiz_id: int, faculty_user_id: int) -> int:
    quiz = Quiz.objects.select_for_update().get(pk=quiz_id)
    if quiz.created_by_user_id != faculty_user_id:
        raise PermissionDeniedError(
            "You can only release results for your own quizzes.", code="NOT_COURSE_OWNER"
        )

    updated = QuizResult.objects.filter(attempt__quiz=quiz, status="EVALUATED").update(
        status="RELEASED"
    )
    AuditLogEntry.objects.create(
        quiz_id=quiz.pk, event="RESULTS_RELEASED", actor_user_id=faculty_user_id
    )
    Notification.objects.create(
        recipient_user_id=faculty_user_id,
        event="RESULTS_RELEASED",
        payload={"quiz_id": quiz.pk, "count": updated},
    )
    return updated
