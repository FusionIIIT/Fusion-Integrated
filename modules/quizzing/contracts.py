"""Contract boundary for the Quizzing module (ADR-0013: No cross-module Foreign Keys)."""
from typing import Dict, Any, List
from .models import QuizAttempt


def get_student_quiz_summary(user_id: str) -> Dict[str, Any]:
    """Public read API exposed to other modules (e.g. Academics / Performance)."""
    attempts = QuizAttempt.objects.filter(student_user_id=user_id, status="EVALUATED")
    total_quizzes = attempts.count()
    total_score = sum(float(a.total_score) for a in attempts)
    average_score = (total_score / total_quizzes) if total_quizzes > 0 else 0.0

    return {
        "user_id": user_id,
        "completed_quizzes_count": total_quizzes,
        "average_score": round(average_score, 2),
    }
