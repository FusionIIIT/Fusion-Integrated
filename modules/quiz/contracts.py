from collections.abc import Sequence

from modules.quiz.models import Quiz, QuizAttempt


def get_student_quiz_summaries(student_ids: Sequence[int]) -> list[dict]:
    """Plural getter: Return student quiz participation and performance summaries."""
    attempts = QuizAttempt.objects.filter(student_id__in=student_ids).select_related(
        "quiz", "result"
    )
    summaries = []
    for att in attempts:
        result = getattr(att, "result", None)
        summaries.append(
            {
                "student_id": att.student_id,
                "quiz_id": att.quiz_id,
                "quiz_title": att.quiz.title,
                "status": att.status,
                "submitted_at": att.submitted_at,
                "marks_obtained": float(result.marks_obtained) if result else None,
                "percentage": float(result.percentage) if result else None,
                "passed": result.passed if result else None,
            }
        )
    return summaries


def get_course_quiz_summaries(course_ids: Sequence[int]) -> list[dict]:
    """Plural getter: Return quiz count and statistics for given courses."""
    quizzes = Quiz.objects.filter(course_id__in=course_ids)
    summaries = []
    for q in quizzes:
        attempts = q.attempts.all()
        summaries.append(
            {
                "course_id": q.course_id,
                "quiz_id": q.pk,
                "title": q.title,
                "status": q.status,
                "attempts_count": attempts.count(),
                "submitted_count": attempts.filter(status="SUBMITTED").count(),
            }
        )
    return summaries
