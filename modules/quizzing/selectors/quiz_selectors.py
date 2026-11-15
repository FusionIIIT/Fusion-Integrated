"""Selectors for quizzing."""

from django.db.models import QuerySet
from modules.quizzing.models import Quiz, QuizAttempt, Question, QuestionBank, AttemptIntegrityLog


def get_student_quizzes(student_id: str) -> QuerySet[Quiz]:
    return Quiz.objects.filter(status__in=["PUBLISHED", "CLOSED"]).order_by("-start_time")


def get_faculty_quizzes(faculty_id: str) -> QuerySet[Quiz]:
    return Quiz.objects.filter(created_by=faculty_id).order_by("-created_at")


def get_quiz_by_id(quiz_id: str) -> Quiz:
    return Quiz.objects.prefetch_related("quiz_questions__question").get(id=quiz_id)


def get_attempt_by_id(attempt_id: str) -> QuizAttempt:
    return QuizAttempt.objects.prefetch_related("answers__question", "quiz").get(id=attempt_id)


def get_quiz_attempts_for_grading(quiz_id: str) -> QuerySet[QuizAttempt]:
    return QuizAttempt.objects.filter(quiz_id=quiz_id).prefetch_related("answers__question").order_by("-submitted_at")


def get_attempt_integrity_logs(attempt_id: str) -> QuerySet[AttemptIntegrityLog]:
    return AttemptIntegrityLog.objects.filter(attempt_id=attempt_id).order_by("timestamp")


def get_question_banks() -> QuerySet[QuestionBank]:
    return QuestionBank.objects.all().order_by("-created_at")
