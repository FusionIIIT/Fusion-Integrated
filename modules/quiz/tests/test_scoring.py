from decimal import Decimal

import pytest

from modules.quiz.scoring import NotObjective, compute_result, score_response


@pytest.mark.parametrize(
    ("question", "answer", "negative", "expected"),
    [
        ({"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}, "A", True, "2.00"),
        ({"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}, "B", True, "-0.50"),
        ({"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}, "B", False, "0.00"),
        ({"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}, None, True, "0.00"),
        ({"type": "MSQ", "marks": 2, "correct": ["A", "B"]}, ["A", "B"], False, "2.00"),
        ({"type": "MSQ", "marks": 2, "correct": ["A", "B"]}, ["A"], False, "0.00"),
        ({"type": "MSQ", "marks": 2, "correct": ["A", "B"]}, ["A", "B", "C"], False, "0.00"),
        ({"type": "FIB", "marks": 2, "correct": ["Paris"]}, "  PARIS ", False, "2.00"),
        ({"type": "FIB", "marks": 2, "correct": ["Paris"]}, "Pariss", False, "0.00"),
    ],
)
def test_objective_scoring(question, answer, negative, expected):
    assert score_response(question, answer, negative) == Decimal(expected)


def test_subjective_questions_are_not_scored():
    with pytest.raises(NotObjective):
        score_response({"type": "SHORT", "marks": 2, "correct": []}, "answer", False)


def test_result_is_floored_and_rounded():
    result = compute_result(
        [Decimal("2"), Decimal("-0.5"), Decimal("2")],
        Decimal("10"),
        Decimal("4"),
        {"correct": 2, "incorrect": 1, "unanswered": 0},
    )
    assert result["marks_obtained"] == Decimal("3.50")
    assert result["percentage"] == Decimal("35.00")
    assert result["passed"] is False
    assert compute_result([Decimal("-1"), Decimal("-1")], 10, 1, {})["marks_obtained"] == Decimal(
        "0.00"
    )
