from decimal import Decimal

import pytest

from modules.quiz.domain.scoring import NotObjective, compute_result, score_response


def test_scoring_objective_mcq():
    q = {
        "type": "MCQ",
        "marks": Decimal("4.00"),
        "negative_marks": Decimal("1.00"),
        "correct": ["B"],
    }
    assert score_response(q, "B", negative_marking_enabled=True) == Decimal("4.00")
    assert score_response(q, "A", negative_marking_enabled=True) == Decimal("-1.00")
    assert score_response(q, "A", negative_marking_enabled=False) == Decimal("0.00")
    assert score_response(q, None, negative_marking_enabled=True) == Decimal("0.00")


def test_scoring_msq():
    q = {
        "type": "MSQ",
        "marks": Decimal("5.00"),
        "negative_marks": Decimal("1.50"),
        "correct": ["A", "C"],
    }
    assert score_response(q, ["A", "C"], negative_marking_enabled=True) == Decimal("5.00")
    assert score_response(q, ["A"], negative_marking_enabled=True) == Decimal("-1.50")


def test_scoring_subjective_raises():
    q = {"type": "SHORT", "marks": 5, "correct": []}
    with pytest.raises(NotObjective):
        score_response(q, "Sample text", negative_marking_enabled=True)


def test_compute_result():
    res = compute_result(
        scores=[Decimal("4.00"), Decimal("-1.00"), Decimal("0.00")],
        max_marks=Decimal("10.00"),
        passing_marks=Decimal("3.00"),
        counts={"correct": 1, "incorrect": 1, "unanswered": 1},
    )
    assert res["marks_obtained"] == Decimal("3.00")
    assert res["negative_marks_total"] == Decimal("1.00")
    assert res["percentage"] == Decimal("30.00")
    assert res["passed"] is True
