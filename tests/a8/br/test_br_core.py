from datetime import datetime, timedelta, timezone

import pytest

from modules.quiz.machines.attempt_machine import M2, STUDENT, SYSTEM
from modules.quiz.scoring import compute_result, score_response
from modules.quiz.state_machine import IllegalTransition, apply_transition


def test_br_qz_011_negative_marking():
    """BR-QZ-011 AFR-QZ-011.1: negative marking is configurable."""
    question = {"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}
    assert score_response(question, "B", True) == -score_response(question, "A", True) / 4
    assert score_response(question, "B", False) == 0


def test_br_qz_016_submitted_attempt_is_immutable():
    """BR-QZ-016 UC-QZ-010: no transition is legal after submission."""
    with pytest.raises(IllegalTransition):
        apply_transition(M2, "SUBMITTED", "submit", STUDENT, {})


def test_br_qz_017_deadline_auto_submit():
    """BR-QZ-017 UC-QZ-011: expiry permits the system submission transition."""
    now = datetime.now(timezone.utc)
    assert apply_transition(M2, "STARTED", "auto_submit", SYSTEM,
                            {"now": now, "deadline_at": now}) == "SUBMITTED"


def test_br_qz_020_result_calculation():
    """BR-QZ-020 AFR-QZ-011.3: marks and percentage are calculated from scores."""
    result = compute_result([2, -0.5, 2], 10, 4,
                            {"correct": 2, "incorrect": 1, "unanswered": 0})
    assert result["marks_obtained"] == 2 + 2 - 0.5
    assert result["percentage"] == 35


@pytest.mark.parametrize("source_id", ["BR-QZ-001", "BR-QZ-002", "BR-QZ-003", "BR-QZ-004",
                                       "BR-QZ-005", "BR-QZ-006", "BR-QZ-007", "BR-QZ-008",
                                       "BR-QZ-009", "BR-QZ-010", "BR-QZ-012", "BR-QZ-013",
                                       "BR-QZ-014", "BR-QZ-015", "BR-QZ-018", "BR-QZ-019",
                                       "BR-QZ-021", "BR-QZ-022", "BR-QZ-023", "BR-QZ-024"])
def test_br_not_automated_without_service_surface(source_id):
    """BR-source-id: service/API obligations are explicitly not automatable in A8_BASE."""
    pytest.skip(f"NOT_AUTOMATED: {source_id} has no corresponding quiz API/service in A8_BASE.")

