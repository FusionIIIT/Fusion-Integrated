"""Contract boundary for the Quizzing module (ADR-0013: No cross-module Foreign Keys)."""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from modules.quizzing.models import QuizAttempt


def get_student_quiz_summaries(user_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Return aggregated quiz performance summaries for the requested student user IDs."""
    if not user_ids:
        return {}

    attempts = QuizAttempt.objects.filter(student_user_id__in=user_ids, status="EVALUATED")
    summaries: dict[str, dict[str, Any]] = {
        uid: {"user_id": uid, "completed_quizzes_count": 0, "average_score": Decimal("0.0")}
        for uid in user_ids
    }

    user_scores: dict[str, list[Decimal]] = {uid: [] for uid in user_ids}
    for attempt in attempts:
        user_scores[attempt.student_user_id].append(attempt.total_score)

    for uid, scores in user_scores.items():
        if scores:
            avg = sum(scores) / Decimal(len(scores))
            summaries[uid] = {
                "user_id": uid,
                "completed_quizzes_count": len(scores),
                "average_score": round(avg, 2),
            }

    return summaries
