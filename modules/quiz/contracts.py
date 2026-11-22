"""Quiz module public contract.

Only functions defined here may be imported by other modules. Plural by signature.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.quiz.models import QuizAttempt


@dataclass(frozen=True)
class QuizPerformanceDTO:
    user_id: int
    quiz_id: int
    quiz_title: str
    quiz_course: str
    attempt_number: int
    score: Decimal | None
    percentage: Decimal | None
    passed: bool | None
    status: str


def get_student_quiz_performances(
    user_ids: Sequence[int],
) -> dict[int, list[QuizPerformanceDTO]]:
    """Return released quiz performance records for the given student user IDs."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    attempts = (
        QuizAttempt.objects.filter(user_id__in=ids, status="released")
        .select_related("quiz")
        .order_by("user_id", "quiz_id", "attempt_number")
    )
    result: dict[int, list[QuizPerformanceDTO]] = {uid: [] for uid in ids}
    for att in attempts:
        result[att.user_id].append(
            QuizPerformanceDTO(
                user_id=att.user_id,
                quiz_id=att.quiz_id,
                quiz_title=att.quiz.title,
                quiz_course=att.quiz.course,
                attempt_number=att.attempt_number,
                score=att.score,
                percentage=att.percentage,
                passed=att.passed,
                status=att.status,
            )
        )
    return result
