from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from modules.quizzing.models import (
    Quiz, QuizQuestion, Question, QuizAttempt, StudentAnswer, AttemptIntegrityLog, QuizStatus, AttemptStatus,
)
from modules.quizzing.domain.rules import validate_quiz_schedule, validate_attempt_window, is_attempt_expired, calculate_autograded_score
from modules.quizzing.domain.state_machine import transition_quiz, transition_attempt


class QuizService:
    @staticmethod
    def create_quiz(title: str, course_code: str, created_by: str, start_time: datetime, end_time: datetime, duration_minutes: int, description: str = "", question_ids: list = None) -> Quiz:
        validate_quiz_schedule(start_time, end_time, duration_minutes)
        with transaction.atomic():
            quiz = Quiz.objects.create(title=title, course_code=course_code, created_by=created_by, start_time=start_time, end_time=end_time, duration_minutes=duration_minutes, description=description)
            total = Decimal("0.0")
            for idx, q_id in enumerate(question_ids or [], start=1):
                q = Question.objects.get(id=q_id)
                QuizQuestion.objects.create(quiz=quiz, question=q, order=idx, marks=q.default_marks)
                total += q.default_marks
            quiz.total_marks = total
            quiz.save(update_fields=["total_marks"])
            return quiz

    @staticmethod
    def publish_quiz(quiz_id: str) -> Quiz:
        quiz = Quiz.objects.get(id=quiz_id)
        transition_quiz(quiz, QuizStatus.PUBLISHED)
        quiz.save(update_fields=["status"])
        return quiz

    @staticmethod
    def start_attempt(quiz_id: str, student_id: str) -> QuizAttempt:
        now, quiz = timezone.now(), Quiz.objects.get(id=quiz_id)
        validate_attempt_window(quiz, now)
        existing = QuizAttempt.objects.filter(quiz=quiz, student_user_id=student_id).first()
        if existing: return existing

        with transaction.atomic():
            attempt = QuizAttempt.objects.create(quiz=quiz, student_user_id=student_id, started_at=now)
            for qq in QuizQuestion.objects.filter(quiz=quiz).select_related("question"):
                StudentAnswer.objects.create(attempt=attempt, question=qq.question, submitted_answer={})
            return attempt

    @staticmethod
    def save_answer(attempt_id: str, question_id: str, submitted_answer: dict) -> StudentAnswer:
        attempt = QuizAttempt.objects.get(id=attempt_id)
        if attempt.status != AttemptStatus.IN_PROGRESS: raise ValueError("Attempt is closed.")
        if is_attempt_expired(attempt, attempt.quiz, timezone.now()):
            QuizService.submit_attempt(attempt_id, autosubmit=True)
            raise ValueError("Time expired.")
        ans, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question_id=question_id)
        ans.submitted_answer = submitted_answer
        ans.save(update_fields=["submitted_answer"])
        return ans

    @staticmethod
    def submit_attempt(attempt_id: str, autosubmit: bool = False) -> QuizAttempt:
        with transaction.atomic():
            attempt = QuizAttempt.objects.select_for_update().get(id=attempt_id)
            if attempt.status in [AttemptStatus.SUBMITTED, AttemptStatus.AUTOSUBMITTED, AttemptStatus.EVALUATED]: return attempt
            transition_attempt(attempt, AttemptStatus.AUTOSUBMITTED if autosubmit else AttemptStatus.SUBMITTED)
            attempt.submitted_at, total = timezone.now(), Decimal("0.0")
            for ans in attempt.answers.select_related("question"):
                ans.autograded_score = calculate_autograded_score(ans.question, ans.submitted_answer)
                ans.save(update_fields=["autograded_score"])
                total += ans.final_score
            attempt.total_score, attempt.status = total, AttemptStatus.EVALUATED
            attempt.save(update_fields=["status", "submitted_at", "total_score"])
            return attempt

    @staticmethod
    def log_integrity_event(attempt_id: str, event_type: str, details: str = "") -> AttemptIntegrityLog:
        return AttemptIntegrityLog.objects.create(attempt_id=attempt_id, event_type=event_type, details=details)

    @staticmethod
    def override_score(answer_id: str, override_score: Decimal, feedback: str = "") -> StudentAnswer:
        ans = StudentAnswer.objects.get(id=answer_id)
        ans.override_score, ans.feedback = override_score, feedback
        ans.save(update_fields=["override_score", "feedback"])
        ans.attempt.total_score = sum(a.final_score for a in ans.attempt.answers.all())
        ans.attempt.save(update_fields=["total_score"])
        return ans

    @staticmethod
    def toggle_release(quiz_id: str, field: str, val: bool) -> Quiz:
        quiz = Quiz.objects.get(id=quiz_id)
        setattr(quiz, field, val)
        quiz.save(update_fields=[field])
        return quiz
