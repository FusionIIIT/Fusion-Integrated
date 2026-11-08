from decimal import Decimal

import pytest

from modules.quiz.scoring import compute_result, score_response


def test_afr_qz_011_1_mcq_negative_marking():
    """FR-AFR-QZ-011.1 BR-QZ-011: MCQ scoring applies configured negative marks."""
    question = {"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}
    assert score_response(question, "A", True) == Decimal("2.00")
    assert score_response(question, "B", True) == Decimal("-0.50")


def test_afr_qz_011_2_msq_is_all_or_nothing():
    """FR-AFR-QZ-011.2 BR-QZ-018: MSQ requires exact set equality."""
    question = {"type": "MSQ", "marks": 2, "correct": ["A", "B"]}
    assert score_response(question, ["A", "B"], False) == Decimal("2.00")
    assert score_response(question, ["A"], False) == Decimal("0.00")
    assert score_response(question, ["A", "B", "C"], False) == Decimal("0.00")


def test_afr_qz_011_3_result_is_floored_and_rounded():
    """FR-AFR-QZ-011.3 BR-QZ-020: result totals floor at zero and round to two places."""
    result = compute_result(
        [Decimal("2"), Decimal("-0.5"), Decimal("2")],
        10,
        4,
        {"correct": 2, "incorrect": 1, "unanswered": 0},
    )
    assert result["marks_obtained"] == Decimal("3.50")
    assert result["percentage"] == Decimal("35.00")
    assert result["passed"] is False


@pytest.mark.parametrize("source_id", ["AFR-QZ-001.1", "AFR-QZ-001.2", "AFR-QZ-001.3", "AFR-QZ-001.4"])
def test_fr_not_automated_without_service_surface(source_id):
    """FR-source-id: authorization API obligations are explicitly not automatable in A8_BASE."""
    pytest.skip(f"NOT_AUTOMATED: {source_id} has no corresponding quiz API/service in A8_BASE.")

