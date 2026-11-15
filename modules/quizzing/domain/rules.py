"""Domain rules for quizzing and autograding."""

from datetime import datetime, timedelta
from decimal import Decimal
from modules.quizzing.models import QuestionType


def validate_quiz_schedule(start_time: datetime, end_time: datetime, duration_minutes: int):
    if end_time <= start_time or duration_minutes <= 0:
        raise ValueError("Invalid quiz schedule: end time must be after start time and duration > 0.")


def validate_attempt_window(quiz, now: datetime):
    if quiz.status != "PUBLISHED" or now < quiz.start_time or now > quiz.end_time:
        raise ValueError("Quiz is not currently available for attempt.")


def is_attempt_expired(attempt, quiz, now: datetime) -> bool:
    if now > quiz.end_time or now > (attempt.started_at + timedelta(minutes=quiz.duration_minutes)):
        return True
    return False


def calculate_autograded_score(question, submitted_answer) -> Decimal:
    if not submitted_answer:
        return Decimal("0.0")
    q_type, correct, marks = question.question_type, question.correct_answer, question.default_marks

    if q_type in [QuestionType.MCQ_SINGLE, QuestionType.TRUE_FALSE]:
        val = submitted_answer.get("choice") or submitted_answer.get("value")
        target = correct.get("choice") or correct.get("value")
        return marks if str(val).strip().lower() == str(target).strip().lower() else Decimal("0.0")

    if q_type == QuestionType.MCQ_MULTI:
        return marks if set(submitted_answer.get("choices", [])) == set(correct.get("choices", [])) else Decimal("0.0")

    if q_type == QuestionType.SHORT_ANSWER:
        ans = str(submitted_answer.get("text", "")).strip().lower()
        target = str(correct.get("model_answer", "")).strip().lower()
        return marks if ans and ans in target or target in ans else Decimal("0.0")

    return Decimal("0.0")
