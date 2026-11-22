"""Domain-layer tests — no database, fast."""
from decimal import Decimal

import pytest

from modules.quiz.domain.errors import (
    InvalidAttemptTransition,
    InvalidQuizTransition,
)
from modules.quiz.domain.evaluation import calculate_result, evaluate_objective
from modules.quiz.domain.state_machine import (
    AttemptStatus,
    QuizStatus,
    validate_attempt_transition,
    validate_quiz_transition,
)

# ---------------------------------------------------------------------------
# State machine — Quiz
# ---------------------------------------------------------------------------

class TestQuizStateMachine:
    def test_draft_to_available_is_valid(self):
        validate_quiz_transition(QuizStatus.DRAFT, QuizStatus.AVAILABLE)

    def test_draft_to_scheduled_is_valid(self):
        validate_quiz_transition(QuizStatus.DRAFT, QuizStatus.SCHEDULED)

    def test_scheduled_to_available_is_valid(self):
        validate_quiz_transition(QuizStatus.SCHEDULED, QuizStatus.AVAILABLE)

    def test_available_to_closed_is_valid(self):
        validate_quiz_transition(QuizStatus.AVAILABLE, QuizStatus.CLOSED)

    def test_closed_to_archived_is_valid(self):
        validate_quiz_transition(QuizStatus.CLOSED, QuizStatus.ARCHIVED)

    def test_draft_to_closed_is_invalid(self):
        with pytest.raises(InvalidQuizTransition):
            validate_quiz_transition(QuizStatus.DRAFT, QuizStatus.CLOSED)

    def test_available_to_archived_is_invalid(self):
        with pytest.raises(InvalidQuizTransition):
            validate_quiz_transition(QuizStatus.AVAILABLE, QuizStatus.ARCHIVED)

    def test_archived_has_no_outgoing(self):
        for target in QuizStatus:
            if target != QuizStatus.ARCHIVED:
                with pytest.raises(InvalidQuizTransition):
                    validate_quiz_transition(QuizStatus.ARCHIVED, target)


# ---------------------------------------------------------------------------
# State machine — Attempt
# ---------------------------------------------------------------------------

class TestAttemptStateMachine:
    def test_in_progress_to_submitted(self):
        validate_attempt_transition(
            AttemptStatus.IN_PROGRESS, AttemptStatus.SUBMITTED
        )

    def test_submitted_to_evaluated(self):
        validate_attempt_transition(
            AttemptStatus.SUBMITTED, AttemptStatus.EVALUATED
        )

    def test_submitted_to_partially_evaluated(self):
        validate_attempt_transition(
            AttemptStatus.SUBMITTED, AttemptStatus.PARTIALLY_EVALUATED
        )

    def test_partially_evaluated_to_evaluated(self):
        validate_attempt_transition(
            AttemptStatus.PARTIALLY_EVALUATED, AttemptStatus.EVALUATED
        )

    def test_evaluated_to_released(self):
        validate_attempt_transition(
            AttemptStatus.EVALUATED, AttemptStatus.RELEASED
        )

    def test_in_progress_to_released_invalid(self):
        with pytest.raises(InvalidAttemptTransition):
            validate_attempt_transition(
                AttemptStatus.IN_PROGRESS, AttemptStatus.RELEASED
            )

    def test_released_has_no_outgoing(self):
        for target in AttemptStatus:
            if target != AttemptStatus.RELEASED:
                with pytest.raises(InvalidAttemptTransition):
                    validate_attempt_transition(AttemptStatus.RELEASED, target)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class TestObjectiveEvaluation:
    M = Decimal("5")
    NM = Decimal("1")

    def test_mcq_correct(self):
        is_correct, marks = evaluate_objective(
            "mcq", correct_answer="A", student_response="A",
            marks=self.M, negative_marks=self.NM,
            negative_marking_enabled=True,
        )
        assert is_correct is True
        assert marks == self.M

    def test_mcq_wrong_with_negative_marking(self):
        is_correct, marks = evaluate_objective(
            "mcq", correct_answer="A", student_response="B",
            marks=self.M, negative_marks=self.NM,
            negative_marking_enabled=True,
        )
        assert is_correct is False
        assert marks == -self.NM

    def test_mcq_wrong_without_negative_marking(self):
        is_correct, marks = evaluate_objective(
            "mcq", correct_answer="A", student_response="B",
            marks=self.M, negative_marks=self.NM,
            negative_marking_enabled=False,
        )
        assert is_correct is False
        assert marks == Decimal("0")

    def test_msq_correct_set(self):
        is_correct, marks = evaluate_objective(
            "msq", correct_answer=["A", "C"], student_response=["C", "A"],
            marks=self.M, negative_marks=self.NM,
            negative_marking_enabled=False,
        )
        assert is_correct is True
        assert marks == self.M

    def test_msq_partial_is_wrong(self):
        is_correct, _ = evaluate_objective(
            "msq", correct_answer=["A", "C"], student_response=["A"],
            marks=self.M, negative_marks=self.NM,
            negative_marking_enabled=False,
        )
        assert is_correct is False

    def test_tf_correct(self):
        is_correct, marks = evaluate_objective(
            "tf", correct_answer="true", student_response="True",
            marks=self.M, negative_marks=Decimal("0"),
            negative_marking_enabled=False,
        )
        assert is_correct is True
        assert marks == self.M

    def test_fitb_case_insensitive(self):
        is_correct, marks = evaluate_objective(
            "fitb", correct_answer="Python", student_response="python",
            marks=self.M, negative_marks=Decimal("0"),
            negative_marking_enabled=False,
        )
        assert is_correct is True
        assert marks == self.M

    def test_short_returns_none(self):
        is_correct, marks = evaluate_objective(
            "short", correct_answer=None, student_response="anything",
            marks=self.M, negative_marks=Decimal("0"),
            negative_marking_enabled=False,
        )
        assert is_correct is None
        assert marks is None

    def test_unanswered_scores_zero(self):
        is_correct, marks = evaluate_objective(
            "mcq", correct_answer="A", student_response=None,
            marks=self.M, negative_marks=self.NM,
            negative_marking_enabled=True,
        )
        assert is_correct is False
        assert marks == Decimal("0")


class TestResultCalculation:
    def test_percentage_calculation(self):
        percentage, passed = calculate_result(
            total_marks_obtained=Decimal("40"),
            max_marks=Decimal("50"),
            passing_marks=Decimal("25"),
        )
        assert percentage == Decimal("80.00")
        assert passed is True

    def test_fail(self):
        _, passed = calculate_result(
            total_marks_obtained=Decimal("20"),
            max_marks=Decimal("50"),
            passing_marks=Decimal("25"),
        )
        assert passed is False

    def test_no_passing_marks_gives_none(self):
        _, passed = calculate_result(
            total_marks_obtained=Decimal("20"),
            max_marks=Decimal("50"),
            passing_marks=None,
        )
        assert passed is None
