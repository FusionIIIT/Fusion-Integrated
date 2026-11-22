from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


class NotObjective(ValueError):
    pass


def _decimal(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def score_response(question: dict, answer, negative_marking_enabled: bool) -> Decimal:
    question_type = question["type"]
    marks = _decimal(question["marks"])
    negative = _decimal(question.get("negative_marks", 0))
    correct = question.get("correct", [])
    if question_type in {"SHORT", "LONG"}:
        raise NotObjective(question_type)
    if answer is None or answer == "":
        return Decimal("0.00")
    if question_type == "FIB":
        is_correct = any(
            str(answer).strip().casefold() == str(item).strip().casefold() for item in correct
        )
    elif question_type == "MSQ":
        is_correct = set(answer) == set(correct)
    else:
        is_correct = answer in correct
    if is_correct:
        return marks
    return -negative if negative_marking_enabled else Decimal("0.00")


def compute_result(scores, max_marks, passing_marks, counts: dict) -> dict:
    marks = sum((_decimal(score) for score in scores), Decimal("0.00"))
    marks = max(Decimal("0.00"), marks)
    maximum = _decimal(max_marks)
    percentage = (
        (marks * Decimal("100") / maximum).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if maximum
        else Decimal("0.00")
    )
    return {
        "marks_obtained": marks,
        "negative_marks_total": sum(
            (-_decimal(score) for score in scores if _decimal(score) < 0), Decimal("0.00")
        ),
        "percentage": percentage,
        "passed": marks >= _decimal(passing_marks),
        "correct_count": counts.get("correct", 0),
        "incorrect_count": counts.get("incorrect", 0),
        "unanswered_count": counts.get("unanswered", 0),
    }
