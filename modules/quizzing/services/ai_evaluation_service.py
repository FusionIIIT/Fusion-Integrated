"""Advisory AI subjective evaluation service (AFR-QZ-012.2)."""

from decimal import Decimal
from typing import Any

from modules.quizzing.models import Question


class AiEvaluationService:
    """Provides advisory AI evaluation suggestions while keeping professor marks final."""

    @staticmethod
    def generate_advisory_evaluation(
        question: Question,
        submitted_answer: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute advisory suggested_marks and evaluation_reasoning based on rubrics."""
        student_text = str(submitted_answer.get("text", "")).strip().lower()
        model_answer = str(question.correct_answer.get("model_answer", "")).strip().lower()
        max_marks = question.default_marks

        if not student_text:
            return {
                "suggested_marks": Decimal("0.0"),
                "evaluation_reasoning": "Answer was left empty; no credit awarded.",
            }

        keywords = [w for w in model_answer.split() if len(w) > 3]
        matched = [w for w in keywords if w in student_text] if keywords else []
        ratio = len(matched) / len(keywords) if keywords else 1.0

        suggested = round(max_marks * Decimal(str(ratio)), 2)
        reasoning = (
            f"Advisory AI evaluation matched {len(matched)}/{len(keywords)} key concepts. "
            "Professor review required for final confirmation."
        )

        return {
            "suggested_marks": suggested,
            "evaluation_reasoning": reasoning,
        }
