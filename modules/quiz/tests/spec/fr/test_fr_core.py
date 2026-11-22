import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.quiz.machines.attempt_machine import M2, SYSTEM
from modules.quiz.machines.attempt_machine import STUDENT as ATTEMPT_STUDENT
from modules.quiz.machines.quiz_machine import M1
from modules.quiz.machines.quiz_machine import SYSTEM as QUIZ_SYSTEM
from modules.quiz.machines.result_machine import M3
from modules.quiz.models import Quiz
from modules.quiz.scope import professor_teaches, student_eligible
from modules.quiz.scoring import NotObjective, compute_result, score_response
from modules.quiz.state_machine import GuardFailed, IllegalTransition, apply_transition

_REPO_ROOT = Path(__file__).resolve().parents[5]
_FR_CASES = json.loads(
    (_REPO_ROOT / "docs" / "20-quiz" / "spec-tests" / "FR_DESIGN.json").read_text(encoding="utf-8")
)["cases"]
_SCORING_TEST_IDS = {
    "FR-AFR-QZ-011.1",
    "FR-AFR-QZ-011.2",
    "FR-AFR-QZ-011.3",
}
_DOMAIN_TEST_IDS = {
    "FR-AFR-QZ-001.2",
    "FR-AFR-QZ-001.3",
    "FR-AFR-QZ-003.2",
    "FR-AFR-QZ-003.3",
    "FR-AFR-QZ-003.4",
    "FR-AFR-QZ-006.1",
    "FR-AFR-QZ-008.1",
    "FR-AFR-QZ-008.2",
    "FR-AFR-QZ-010.4",
    "FR-AFR-QZ-013.2",
    "FR-AFR-QZ-013.3",
}


def test_fr_afr_qz_011_1_objective_scoring_applies_negative_marks():
    """FR-AFR-QZ-011.1 / AFR-QZ-011.1: partial scoring check, not submit-trigger/API coverage."""
    question = {"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}
    assert score_response(question, "A", True) == Decimal("2.00")
    assert score_response(question, "B", True) == Decimal("-0.50")
    assert score_response(question, "B", False) == Decimal("0.00")

    assert score_response({"type": "TF", "marks": 1, "correct": [True]}, True, False) == Decimal(
        "1.00"
    )
    assert score_response(
        {"type": "FIB", "marks": 2, "correct": ["Paris"]}, " PARIS ", False
    ) == Decimal("2.00")
    msq = {"type": "MSQ", "marks": 2, "correct": ["A", "B"]}
    assert score_response(msq, ["A", "B"], False) == Decimal("2.00")
    assert score_response(msq, ["A"], False) == Decimal("0.00")
    assert score_response(msq, ["A", "B", "C"], False) == Decimal("0.00")
    with pytest.raises(NotObjective):
        score_response({"type": "SHORT", "marks": 2, "correct": []}, "answer", False)


def test_fr_afr_qz_011_2_negative_marks_and_exact_msq_match():
    """FR-AFR-QZ-011.2 / AFR-QZ-011.2: partial scoring check, not settings-API coverage."""
    question = {"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}
    assert score_response(question, "A", True) == Decimal("2.00")
    assert score_response(question, "B", True) == Decimal("-0.50")
    assert score_response(question, "B", False) == Decimal("0.00")

    msq = {"type": "MSQ", "marks": 2, "correct": ["A", "B"]}
    assert score_response(msq, ["A", "B"], False) == Decimal("2.00")
    assert score_response(msq, ["A"], False) == Decimal("0.00")
    assert score_response(msq, ["A", "B", "C"], False) == Decimal("0.00")


def test_fr_afr_qz_011_3_result_totals_are_floored_and_rounded():
    """FR-AFR-QZ-011.3 / AFR-QZ-011.3: partial calculation check, not persistence coverage."""
    result = compute_result(
        [Decimal("2"), Decimal("-0.5"), Decimal("2")],
        10,
        4,
        {"correct": 2, "incorrect": 1, "unanswered": 0},
    )
    assert result["marks_obtained"] == Decimal("3.50")
    assert result["percentage"] == Decimal("35.00")
    assert result["passed"] is False
    assert compute_result([Decimal("-1"), Decimal("-1")], 10, 1, {})["marks_obtained"] == Decimal(
        "0.00"
    )


def test_fr_afr_qz_001_2_professor_course_scope():
    """test_id FR-AFR-QZ-001.2; source_id AFR-QZ-001.2. Pure scope helper only."""
    professor = SimpleNamespace(user_id=101)
    associated_course = SimpleNamespace(faculty_ids=(101, 202))
    unrelated_course = SimpleNamespace(faculty_ids=(202,))
    assert professor_teaches(professor, associated_course)
    assert not professor_teaches(professor, unrelated_course)
    assert not professor_teaches(professor, None)


def test_fr_afr_qz_001_3_student_eligibility_scope():
    """test_id FR-AFR-QZ-001.3; source_id AFR-QZ-001.3. Pure eligibility helper only."""
    student = SimpleNamespace(user_id=303, kind="student")
    eligible_quiz = SimpleNamespace(course=SimpleNamespace(student_ids=(303, 404)))
    ineligible_quiz = SimpleNamespace(course=SimpleNamespace(student_ids=(404,)))
    non_student = SimpleNamespace(user_id=303, kind="professor")
    assert student_eligible(student, eligible_quiz)
    assert not student_eligible(student, ineligible_quiz)
    assert not student_eligible(non_student, eligible_quiz)
    assert not student_eligible(student, SimpleNamespace(course=None))


def test_fr_afr_qz_003_2_publish_quiz_immediately_or_scheduled():
    """test_id FR-AFR-QZ-003.2; source_id AFR-QZ-003.2. M1 publish transition only."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    context = {
        "now": now,
        "start_at": now,
        "owns_course": True,
        "questions_valid": True,
        "config_valid": True,
    }
    assert apply_transition(M1, "READY_TO_PUBLISH", "publish", "PROFESSOR", context) == "AVAILABLE"
    context["start_at"] = now + timedelta(hours=1)
    assert apply_transition(M1, "READY_TO_PUBLISH", "publish", "PROFESSOR", context) == "SCHEDULED"


def test_fr_afr_qz_003_3_start_and_close_at_boundaries():
    """test_id FR-AFR-QZ-003.3; source_id AFR-QZ-003.3. M1 boundary transitions only."""
    start_at = datetime(2026, 1, 1, tzinfo=UTC)
    close_at = start_at + timedelta(hours=2)
    context = {"now": start_at, "start_at": start_at}
    assert apply_transition(M1, "SCHEDULED", "boundary_start", QUIZ_SYSTEM, context) == "AVAILABLE"

    context = {"now": close_at, "close_at": close_at}
    assert apply_transition(M1, "AVAILABLE", "boundary_close", QUIZ_SYSTEM, context) == "CLOSED"


def test_fr_afr_qz_003_4_archive_permitted_quiz():
    """test_id FR-AFR-QZ-003.4; source_id AFR-QZ-003.4. Archive only; delete is unavailable."""
    context = {"archive_permitted": True}
    assert apply_transition(M1, "CLOSED", "archive", "PROFESSOR", context) == "ARCHIVED"


def test_fr_afr_qz_006_1_quiz_model_exposes_time_and_attempt_configuration():
    """test_id FR-AFR-QZ-006.1; source_id AFR-QZ-006.1. Metadata only, not persistence coverage."""
    duration = Quiz._meta.get_field("duration_minutes")
    attempts = Quiz._meta.get_field("max_attempts")
    assert duration.get_internal_type() == "PositiveIntegerField"
    assert duration.default == 30
    assert attempts.get_internal_type() == "PositiveSmallIntegerField"
    assert attempts.default == 1
    assert {constraint.name for constraint in Quiz._meta.constraints} >= {
        "quiz_duration_positive",
        "quiz_attempts_positive",
    }


def test_fr_afr_qz_008_1_start_guard_requires_availability():
    """test_id FR-AFR-QZ-008.1; source_id AFR-QZ-008.1. M2 start guard only."""
    start_at = datetime(2026, 1, 1, 1, tzinfo=UTC)
    with pytest.raises(GuardFailed, match="NOT_AVAILABLE"):
        apply_transition(
            M2,
            None,
            "start",
            ATTEMPT_STUDENT,
            {
                "eligible": True,
                "attempts_used": 0,
                "max_attempts": 1,
                "has_active_attempt": False,
                "now": start_at - timedelta(seconds=1),
                "quiz_start_at": start_at,
            },
        )


def test_fr_afr_qz_008_2_start_guard_enforces_attempt_limit():
    """test_id FR-AFR-QZ-008.2; source_id AFR-QZ-008.2. M2 attempt-limit guard only."""
    context = {
        "eligible": True,
        "attempts_used": 2,
        "max_attempts": 2,
        "has_active_attempt": False,
        "now": datetime(2026, 1, 1, tzinfo=UTC),
    }
    with pytest.raises(GuardFailed, match="ATTEMPTS_EXHAUSTED"):
        apply_transition(M2, None, "start", ATTEMPT_STUDENT, context)

    context["attempts_used"] = 1
    assert apply_transition(M2, None, "start", ATTEMPT_STUDENT, context) == "STARTED"


def test_fr_afr_qz_010_4_auto_submit_at_deadline():
    """test_id FR-AFR-QZ-010.4; source_id AFR-QZ-010.4. M2 deadline transition only."""
    deadline = datetime(2026, 1, 1, 1, tzinfo=UTC)
    context = {"now": deadline - timedelta(seconds=1), "deadline_at": deadline}
    context["now"] = deadline
    assert apply_transition(M2, "STARTED", "auto_submit", SYSTEM, context) == "SUBMITTED"


def test_fr_afr_qz_013_2_result_evaluation_lifecycle_transitions():
    """test_id FR-AFR-QZ-013.2; source_id AFR-QZ-013.2. M3 state transitions only."""
    assert apply_transition(M3, "NOT_EVALUATED", "auto_evaluate", SYSTEM, {}) == "EVALUATED"
    assert apply_transition(M3, "PARTIALLY_EVALUATED", "auto_evaluate", SYSTEM, {}) == "EVALUATED"


def test_fr_afr_qz_013_3_professor_can_release_evaluated_result():
    """test_id FR-AFR-QZ-013.3; source_id AFR-QZ-013.3. Permitted M3 release transition only."""
    assert apply_transition(M3, "EVALUATED", "release", "PROFESSOR", {"owns_course": True}) == (
        "RELEASED"
    )
    with pytest.raises(IllegalTransition):
        apply_transition(M3, "EVALUATED", "release", "STUDENT", {"owns_course": True})
