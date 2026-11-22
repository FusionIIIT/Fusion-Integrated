"""Objective question auto-evaluation — pure Python, no Django imports."""
from decimal import Decimal
from typing import Any


def evaluate_objective(
    question_type: str,
    correct_answer: Any,
    student_response: Any,
    marks: Decimal,
    negative_marks: Decimal,
    negative_marking_enabled: bool,
) -> tuple[bool | None, Decimal | None]:
    """Evaluate a single objective response.

    Returns (is_correct, marks_obtained).
    For subjective (short) questions returns (None, None) — professor evaluates.
    """
    if question_type == "short":
        return None, None

    if student_response is None:
        # Unanswered: not wrong, just blank
        return False, Decimal("0")

    is_correct = _check_correctness(question_type, correct_answer, student_response)

    if is_correct:
        return True, marks
    deduction = negative_marks if negative_marking_enabled else Decimal("0")
    return False, -deduction


def _check_correctness(
    question_type: str,
    correct_answer: Any,
    student_response: Any,
) -> bool:
    if question_type == "mcq":
        # correct_answer is a string option id
        return str(student_response) == str(correct_answer)

    if question_type == "msq":
        # correct_answer is a list of option ids; order-independent
        correct_set = {str(x) for x in (correct_answer or [])}
        response_set = {str(x) for x in (student_response or [])}
        return correct_set == response_set

    if question_type == "tf":
        # correct_answer is "true" or "false"
        return str(student_response).lower() == str(correct_answer).lower()

    if question_type == "fitb":
        # Case-insensitive exact match
        return (
            str(student_response).strip().lower()
            == str(correct_answer).strip().lower()
        )

    # Unknown type — cannot evaluate
    return False


def calculate_result(
    total_marks_obtained: Decimal,
    max_marks: Decimal,
    passing_marks: Decimal | None,
) -> tuple[Decimal, bool | None]:
    """Calculate percentage and pass/fail from total marks obtained."""
    if max_marks and max_marks > 0:
        percentage = (total_marks_obtained / max_marks) * 100
    else:
        percentage = Decimal("0")

    passed: bool | None = None
    if passing_marks is not None:
        passed = total_marks_obtained >= passing_marks

    return percentage.quantize(Decimal("0.01")), passed
