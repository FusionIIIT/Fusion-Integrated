"""Domain service managing state modifications, transactional integrity, and grading."""

import random
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.quizzing.domain.rules import (
    DomainRuleError,
    calculate_autograded_score,
    can_release_grades,
    check_integrity_threshold,
    determine_pass_fail,
    is_attempt_expired,
    validate_attempt_limit,
    validate_attempt_window,
    validate_linear_navigation,
    validate_quiz_schedule,
    validate_submission_completeness,
)
from modules.quizzing.domain.state_machine import (
    AttemptState,
    QuizState,
    transition_attempt,
    transition_quiz,
)
from modules.quizzing.models import (
    AttemptIntegrityLog,
    Question,
    QuestionBank,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    StudentAnswer,
)
from modules.quizzing.services.ai_evaluation_service import AiEvaluationService


class QuizService:
    """Service layer coordinating business operations for Quizzing."""

    @staticmethod
    def create_question_bank(
        course_code: str,
        title: str,
        created_by: str,
        description: str = "",
    ) -> QuestionBank:
        return QuestionBank.objects.create(
            course_code=course_code,
            title=title,
            created_by=created_by,
            description=description,
        )

    @staticmethod
    def create_question(
        bank_id: str | None,
        question_text: str,
        question_type: str,
        options: list | None = None,
        correct_answer: dict | None = None,
        default_marks: Decimal = Decimal("1.0"),
        negative_marks: Decimal = Decimal("0.0"),
        difficulty: str = "MEDIUM",
    ) -> Question:
        return Question.objects.create(
            bank_id=bank_id,
            question_text=question_text,
            question_type=question_type,
            options=options or [],
            correct_answer=correct_answer or {},
            default_marks=default_marks,
            negative_marks=negative_marks,
            difficulty=difficulty,
        )

    @staticmethod
    def create_quiz(
        title: str,
        course_code: str,
        created_by: str,
        start_time: datetime,
        end_time: datetime,
        duration_minutes: int,
        description: str = "",
        passing_marks: Decimal = Decimal("0.0"),
        max_attempts: int = 1,
        navigation_mode: str = "FREE",
        randomize_questions: bool = False,
        allow_unanswered: bool = True,
        negative_marking_percentage: Decimal = Decimal("0.0"),
        question_ids: list[str] | None = None,
    ) -> Quiz:
        validate_quiz_schedule(start_time, end_time, duration_minutes)
        with transaction.atomic():
            quiz = Quiz.objects.create(
                title=title,
                course_code=course_code,
                created_by=created_by,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                description=description,
                passing_marks=passing_marks,
                max_attempts=max_attempts,
                navigation_mode=navigation_mode,
                randomize_questions=randomize_questions,
                allow_unanswered=allow_unanswered,
                negative_marking_percentage=negative_marking_percentage,
            )
            total = Decimal("0.0")
            for idx, q_id in enumerate(question_ids or [], start=1):
                q = Question.objects.get(id=q_id)
                QuizQuestion.objects.create(
                    quiz=quiz,
                    question=q,
                    order=idx,
                    marks=q.default_marks,
                )
                total += q.default_marks
            quiz.total_marks = total
            quiz.save(update_fields=["total_marks"])
            return quiz

    @staticmethod
    def publish_quiz(quiz_id: str, actor_id: str | None = None) -> Quiz:
        with transaction.atomic():
            quiz = Quiz.objects.select_for_update().get(id=quiz_id)
            if actor_id and quiz.created_by != actor_id:
                raise PermissionError("Only the quiz author can publish this quiz.")
            if not quiz.quiz_questions.exists():
                raise DomainRuleError(
                    "Cannot publish an empty quiz. Please add at least one question."
                )
            transition_quiz(quiz, QuizState.PUBLISHED)
            quiz.save(update_fields=["status"])
            return quiz

    @staticmethod
    def close_quiz(quiz_id: str, actor_id: str | None = None) -> Quiz:
        with transaction.atomic():
            quiz = Quiz.objects.select_for_update().get(id=quiz_id)
            if actor_id and quiz.created_by != actor_id:
                raise PermissionError("Only the quiz author can close this quiz.")
            transition_quiz(quiz, QuizState.CLOSED)
            quiz.save(update_fields=["status"])
            return quiz

    @staticmethod
    def archive_quiz(quiz_id: str, actor_id: str | None = None) -> Quiz:
        with transaction.atomic():
            quiz = Quiz.objects.select_for_update().get(id=quiz_id)
            if actor_id and quiz.created_by != actor_id:
                raise PermissionError("Only the quiz author can archive this quiz.")
            transition_quiz(quiz, QuizState.ARCHIVED)
            quiz.save(update_fields=["status"])
            return quiz

    @staticmethod
    def start_attempt(quiz_id: str, student_id: str) -> QuizAttempt:
        now = timezone.now()
        with transaction.atomic():
            quiz = Quiz.objects.select_for_update().get(id=quiz_id)
            validate_attempt_window(quiz.status, quiz.start_time, quiz.end_time, now)

            existing_active = QuizAttempt.objects.filter(
                quiz=quiz,
                student_user_id=student_id,
                status=AttemptState.IN_PROGRESS,
            ).first()
            if existing_active:
                return existing_active

            past_attempts_count = QuizAttempt.objects.filter(
                quiz=quiz,
                student_user_id=student_id,
            ).count()
            validate_attempt_limit(past_attempts_count, quiz.max_attempts)

            attempt = QuizAttempt.objects.create(
                quiz=quiz,
                student_user_id=student_id,
                attempt_number=past_attempts_count + 1,
                started_at=now,
            )

            qq_list = list(QuizQuestion.objects.filter(quiz=quiz).select_related("question"))
            if quiz.randomize_questions:
                random.shuffle(qq_list)

            for qq in qq_list:
                StudentAnswer.objects.create(
                    attempt=attempt,
                    question=qq.question,
                    submitted_answer={},
                )
            return attempt

    @staticmethod
    def save_answer(
        attempt_id: str,
        arg2: str,
        arg3: dict | str,
        arg4: dict | None = None,
    ) -> StudentAnswer:
        if isinstance(arg3, dict) and arg4 is None:
            student_id = None
            question_id = arg2
            submitted_answer = arg3
        else:
            student_id = arg2
            question_id = str(arg3)
            submitted_answer = arg4 or {}

        now = timezone.now()
        with transaction.atomic():
            attempt = (
                QuizAttempt.objects.select_for_update()
                .select_related("quiz")
                .get(id=attempt_id)
            )
            if student_id and attempt.student_user_id != student_id:
                raise PermissionError("Access denied to another student's attempt.")
            if attempt.status != AttemptState.IN_PROGRESS:
                raise DomainRuleError("Attempt is already closed. Answers cannot be updated.")

            if is_attempt_expired(
                attempt.started_at,
                attempt.quiz.duration_minutes,
                attempt.quiz.end_time,
                now,
            ):
                QuizService.submit_attempt(attempt_id, autosubmit=True)
                raise DomainRuleError(
                    "Quiz time has expired. Your attempt has been auto-submitted."
                )

            quiz_q = QuizQuestion.objects.filter(
                quiz=attempt.quiz,
                question_id=question_id,
            ).first()
            current_order = quiz_q.order if quiz_q else 0
            if attempt.quiz.navigation_mode == "LINEAR":
                validate_linear_navigation(current_order, attempt.last_answered_order)

            ans, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question_id=question_id)
            ans.submitted_answer = submitted_answer
            ans.save(update_fields=["submitted_answer"])

            if current_order > attempt.last_answered_order:
                attempt.last_answered_order = current_order
                attempt.save(update_fields=["last_answered_order"])

            return ans

    @staticmethod
    def submit_attempt(
        attempt_id: str,
        student_id: str | None = None,
        autosubmit: bool = False,
    ) -> QuizAttempt:
        now = timezone.now()
        with transaction.atomic():
            attempt = (
                QuizAttempt.objects.select_for_update()
                .select_related("quiz")
                .prefetch_related("answers__question")
                .get(id=attempt_id)
            )

            if student_id and attempt.student_user_id != student_id:
                raise PermissionError("Access denied to submit another student's attempt.")

            if attempt.status in [
                AttemptState.SUBMITTED,
                AttemptState.AUTOSUBMITTED,
                AttemptState.EVALUATED,
            ]:
                return attempt

            all_answers = list(attempt.answers.all())
            answered_count = sum(1 for a in all_answers if bool(a.submitted_answer))

            if not autosubmit:
                validate_submission_completeness(
                    answered_count=answered_count,
                    total_count=len(all_answers),
                    allow_unanswered=attempt.quiz.allow_unanswered,
                )

            target_status = AttemptState.AUTOSUBMITTED if autosubmit else AttemptState.SUBMITTED
            transition_attempt(attempt, target_status)
            attempt.submitted_at = now

            has_subjective = any(
                a.question.question_type in ["SHORT_ANSWER", "SUBJECTIVE"]
                for a in all_answers
            )

            total = Decimal("0.0")
            for ans in all_answers:
                q = ans.question
                if q.question_type in ["SHORT_ANSWER", "SUBJECTIVE"]:
                    ans.is_evaluated = False
                    ans.save(update_fields=["is_evaluated"])
                else:
                    ans.autograded_score = calculate_autograded_score(
                        question_type=q.question_type,
                        correct_answer=q.correct_answer,
                        default_marks=q.default_marks,
                        negative_marks=q.negative_marks,
                        submitted_answer=ans.submitted_answer,
                    )
                    ans.is_evaluated = True
                    ans.save(update_fields=["autograded_score", "is_evaluated"])
                    total += ans.final_score

            if has_subjective:
                transition_attempt(attempt, AttemptState.UNDER_REVIEW)
                attempt.total_score = total
                attempt.passed = False
            else:
                transition_attempt(attempt, AttemptState.EVALUATED)
                attempt.total_score = total
                attempt.passed = determine_pass_fail(total, attempt.quiz.passing_marks)

            attempt.save(update_fields=["status", "submitted_at", "total_score", "passed"])
            return attempt

    @staticmethod
    def override_score(
        answer_id: str,
        faculty_id: str,
        override_score: Decimal,
        feedback: str = "",
    ) -> StudentAnswer:
        with transaction.atomic():
            ans = (
                StudentAnswer.objects.select_for_update()
                .select_related("attempt__quiz", "question")
                .get(id=answer_id)
            )
            quiz = ans.attempt.quiz
            if quiz.created_by != faculty_id:
                raise PermissionError("Only the quiz author can evaluate answers.")

            ans.override_score = Decimal(str(override_score))
            ans.feedback = feedback
            ans.is_evaluated = True
            ans.save(update_fields=["override_score", "feedback", "is_evaluated"])

            attempt = ans.attempt
            all_answers = list(attempt.answers.all())
            new_total = sum(a.final_score for a in all_answers)
            attempt.total_score = new_total
            attempt.passed = determine_pass_fail(new_total, quiz.passing_marks)

            all_evaluated = all(a.is_evaluated for a in all_answers)
            if all_evaluated and attempt.status == AttemptState.UNDER_REVIEW:
                transition_attempt(attempt, AttemptState.EVALUATED)

            attempt.save(update_fields=["total_score", "passed", "status"])
            return ans

    @staticmethod
    def request_ai_evaluation(answer_id: str, faculty_id: str) -> dict[str, Any]:
        ans = StudentAnswer.objects.select_related("attempt__quiz", "question").get(id=answer_id)
        if ans.attempt.quiz.created_by != faculty_id:
            raise PermissionError("Only the quiz author can request AI evaluations.")
        return AiEvaluationService.generate_advisory_evaluation(ans.question, ans.submitted_answer)

    @staticmethod
    def log_integrity_event(
        attempt_id: str,
        student_id: str,
        event_type: str,
        details: str = "",
    ) -> AttemptIntegrityLog:
        with transaction.atomic():
            attempt = QuizAttempt.objects.select_for_update().get(id=attempt_id)
            if attempt.student_user_id != student_id:
                raise PermissionError("Integrity audit denied for external student.")

            log_entry = AttemptIntegrityLog.objects.create(
                attempt=attempt,
                event_type=event_type,
                details=details,
            )

            count = AttemptIntegrityLog.objects.filter(attempt=attempt).count()
            if check_integrity_threshold(count, threshold=3) and not attempt.flagged_for_integrity:
                attempt.flagged_for_integrity = True
                attempt.save(update_fields=["flagged_for_integrity"])

            return log_entry

    @staticmethod
    def toggle_release(quiz_id: str, faculty_id: str, field: str, value: bool) -> Quiz:
        with transaction.atomic():
            quiz = Quiz.objects.select_for_update().get(id=quiz_id)
            if quiz.created_by != faculty_id:
                raise PermissionError("Only the quiz author can release grades or answer keys.")

            if field == "grades_released" and value is True:
                pending_count = QuizAttempt.objects.filter(
                    quiz=quiz,
                    status=AttemptState.UNDER_REVIEW,
                ).count()
                if not can_release_grades(pending_count):
                    raise DomainRuleError(
                        f"Cannot release grades: {pending_count} attempt(s) remain under review. "
                        "Please complete subjective evaluations first."
                    )
                quiz.grades_released = True
            elif field == "answer_key_released":
                quiz.answer_key_released = value

            quiz.save(update_fields=[field])
            return quiz
