"""Read selectors for quizzes, questions, and attempts with strict scoping isolation."""

from django.db.models import QuerySet

from modules.quizzing.models import (
    AttemptIntegrityLog,
    Question,
    QuestionBank,
    Quiz,
    QuizAttempt,
    QuizStatus,
)


def get_student_quizzes(student_id: str) -> QuerySet[Quiz]:
    """Return published or closed quizzes available to students."""
    return (
        Quiz.objects.filter(status__in=[QuizStatus.PUBLISHED, QuizStatus.CLOSED])
        .prefetch_related("quiz_questions")
        .order_by("-start_time")
    )


def get_faculty_quizzes(faculty_id: str) -> QuerySet[Quiz]:
    """Return quizzes authored by the designated faculty member."""
    return (
        Quiz.objects.filter(created_by=faculty_id)
        .prefetch_related("quiz_questions")
        .order_by("-created_at")
    )


def get_quiz_by_id(quiz_id: str) -> Quiz:
    """Retrieve quiz by primary key."""
    return Quiz.objects.prefetch_related("quiz_questions__question").get(id=quiz_id)


def get_quiz_for_actor(quiz_id: str, actor_id: str, is_faculty: bool = False) -> Quiz:
    """Retrieve quiz scoped by actor identity to enforce ownership isolation."""
    qs = Quiz.objects.prefetch_related("quiz_questions__question")
    if is_faculty:
        return qs.get(id=quiz_id, created_by=actor_id)
    return qs.get(id=quiz_id, status__in=[QuizStatus.PUBLISHED, QuizStatus.CLOSED])


def get_attempt_by_id(attempt_id: str) -> QuizAttempt:
    """Retrieve attempt by primary key."""
    return QuizAttempt.objects.prefetch_related("answers__question", "quiz").get(id=attempt_id)


def get_attempt_for_actor(
    attempt_id: str,
    actor_id: str,
    is_faculty: bool = False,
) -> QuizAttempt:
    """Retrieve attempt scoped to student owner or faculty author (404 on mismatch)."""
    qs = QuizAttempt.objects.prefetch_related("answers__question", "quiz")
    if is_faculty:
        return qs.get(id=attempt_id, quiz__created_by=actor_id)
    return qs.get(id=attempt_id, student_user_id=actor_id)


def get_quiz_attempts_for_grading(quiz_id: str, faculty_id: str) -> QuerySet[QuizAttempt]:
    """Retrieve all submissions for a quiz authored by the requesting faculty."""
    if not Quiz.objects.filter(id=quiz_id, created_by=faculty_id).exists():
        raise Quiz.DoesNotExist("Quiz not found or unauthorized for grading.")
    return (
        QuizAttempt.objects.filter(quiz_id=quiz_id)
        .prefetch_related("answers__question")
        .order_by("-submitted_at")
    )


def get_attempt_integrity_logs(
    attempt_id: str,
    actor_id: str,
    is_faculty: bool = False,
) -> QuerySet[AttemptIntegrityLog]:
    """Retrieve integrity audit events for an authorized attempt."""
    get_attempt_for_actor(attempt_id, actor_id, is_faculty=is_faculty)
    return AttemptIntegrityLog.objects.filter(attempt_id=attempt_id).order_by("timestamp")


def get_question_banks(faculty_id: str | None = None) -> QuerySet[QuestionBank]:
    """Retrieve question banks optionally scoped to author."""
    qs = QuestionBank.objects.all().prefetch_related("questions")
    if faculty_id:
        qs = qs.filter(created_by=faculty_id)
    return qs.order_by("-created_at")


def get_questions_for_bank(bank_id: str) -> QuerySet[Question]:
    """Retrieve questions belonging to a specific bank."""
    return Question.objects.filter(bank_id=bank_id).order_by("-created_at")
