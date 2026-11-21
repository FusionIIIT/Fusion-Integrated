"""Independent unit tests for the pure Quiz Management domain."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from modules.quiz.domain.attempts import (
    calculate_attempt_deadline,
    deadline_reached,
    require_attempt_eligibility,
)
from modules.quiz.domain.errors import (
    ActorNotAllowed,
    AttemptEligibilityError,
    DefinitionValidationError,
    DomainError,
    GuardFailed,
    InvalidTransition,
    UnresolvedPolicyError,
)
from modules.quiz.domain.quiz_definition import (
    DefinitionAction,
    QuizDefinition,
    is_aware,
    validate_quiz_definition,
)
from modules.quiz.domain.scoring import QuestionType, score_objective_response
from modules.quiz.domain.state_machine import (
    AttemptEvent,
    QuizEvent,
    ResultEvent,
    transition_attempt,
    transition_quiz,
    transition_result,
)
from modules.quiz.domain.types import AttemptStatus, DomainActor, QuizStatus, ResultStatus

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def test_quiz_transition_requires_declared_actor_and_guards() -> None:
    assert transition_quiz(None, QuizEvent.CREATE_DRAFT, DomainActor.PROFESSOR) is QuizStatus.DRAFT
    guards = {"valid_for_publication": True, "within_availability_window": True}
    assert (
        transition_quiz(
            QuizStatus.DRAFT,
            QuizEvent.PUBLISH_NOW,
            DomainActor.PROFESSOR,
            guard_results=guards,
        )
        is QuizStatus.AVAILABLE
    )
    with pytest.raises(GuardFailed):
        transition_quiz(QuizStatus.DRAFT, QuizEvent.PUBLISH_NOW, DomainActor.PROFESSOR)
    with pytest.raises(ActorNotAllowed):
        transition_quiz(QuizStatus.DRAFT, QuizEvent.SCHEDULE, DomainActor.STUDENT)
    with pytest.raises(InvalidTransition):
        transition_quiz(QuizStatus.CLOSED, QuizEvent.PUBLISH_NOW, DomainActor.PROFESSOR)


def test_attempt_transition_and_close_preserve_in_progress_state() -> None:
    with pytest.raises(GuardFailed):
        transition_attempt(None, AttemptEvent.START, DomainActor.STUDENT)
    assert (
        transition_attempt(
            None,
            AttemptEvent.START,
            DomainActor.STUDENT,
            guard_results={
                "eligible": True,
                "available_before_close": True,
                "attempts_remaining": True,
            },
        )
        is AttemptStatus.IN_PROGRESS
    )
    assert (
        transition_attempt(
            AttemptStatus.IN_PROGRESS,
            AttemptEvent.QUIZ_CLOSED,
            DomainActor.SYSTEM,
            guard_results={"close_boundary_reached": True},
        )
        is AttemptStatus.IN_PROGRESS
    )
    with pytest.raises(ActorNotAllowed):
        transition_attempt(
            AttemptStatus.IN_PROGRESS,
            AttemptEvent.AUTO_SUBMIT_DEADLINE,
            DomainActor.STUDENT,
        )
    with pytest.raises(InvalidTransition):
        transition_attempt(AttemptStatus.SUBMITTED, AttemptEvent.START, DomainActor.STUDENT)


def test_result_transitions_require_professor_for_finalization_and_release() -> None:
    assert (
        transition_result(None, ResultEvent.CREATE_ON_SUBMISSION, DomainActor.SYSTEM)
        is ResultStatus.NOT_EVALUATED
    )
    with pytest.raises(GuardFailed):
        transition_result(
            ResultStatus.NOT_EVALUATED,
            ResultEvent.OBJECTIVE_COMPLETE,
            DomainActor.SYSTEM,
        )
    assert (
        transition_result(
            ResultStatus.NOT_EVALUATED,
            ResultEvent.SUBJECTIVE_FINALIZED,
            DomainActor.PROFESSOR,
            guard_results={
                "course_scope_verified": True,
                "marks_valid": True,
                "audit_recordable": True,
            },
        )
        is ResultStatus.EVALUATED
    )
    with pytest.raises(ActorNotAllowed):
        transition_result(ResultStatus.EVALUATED, ResultEvent.RELEASE, DomainActor.STUDENT)
    with pytest.raises(InvalidTransition):
        transition_result(ResultStatus.RELEASED, ResultEvent.RELEASE, DomainActor.PROFESSOR)


def test_is_aware_safely_rejects_non_datetime_values() -> None:
    assert is_aware(NOW)
    assert not is_aware(datetime(2026, 11, 21, 12, 0))
    assert not is_aware("2026-11-21T12:00:00Z")
    assert not is_aware(None)


def valid_definition(**overrides: object) -> QuizDefinition:
    values: dict[str, object] = {
        "title": "Quiz 1",
        "course_id": 5,
        "duration_seconds": 600,
        "maximum_marks": Decimal("10"),
        "passing_marks": Decimal("5"),
        "permitted_attempts": 1,
        "start_at": NOW,
        "close_at": NOW + timedelta(hours=1),
    }
    values.update(overrides)
    return QuizDefinition(**values)  # type: ignore[arg-type]


def test_draft_save_allows_incomplete_definition() -> None:
    validate_quiz_definition(QuizDefinition(), action=DefinitionAction.DRAFT_SAVE)


def test_publication_requires_a_valid_window_and_uses_half_open_boundaries() -> None:
    definition = valid_definition()
    validate_quiz_definition(
        definition,
        action=DefinitionAction.PUBLISH_NOW,
        now=NOW,
    )
    with pytest.raises(DefinitionValidationError):
        validate_quiz_definition(
            definition,
            action=DefinitionAction.PUBLISH_NOW,
            now=definition.close_at,
        )
    validate_quiz_definition(
        valid_definition(start_at=NOW + timedelta(minutes=1)),
        action=DefinitionAction.SCHEDULE,
        now=NOW,
    )
    with pytest.raises(DefinitionValidationError):
        validate_quiz_definition(
            definition,
            action=DefinitionAction.SCHEDULE,
            now=NOW,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", 42),
        ("title", "   "),
        ("title", "x" * 251),
        ("course_id", True),
        ("duration_seconds", 1.5),
        ("maximum_marks", float("nan")),
        ("passing_marks", Decimal("NaN")),
        ("permitted_attempts", False),
    ],
)
def test_definition_rejects_invalid_scalar_values(field: str, value: object) -> None:
    with pytest.raises(DefinitionValidationError) as error:
        validate_quiz_definition(
            valid_definition(**{field: value}),
            action=DefinitionAction.DRAFT_SAVE,
        )
    assert field in {name for name, _ in error.value.issues}


def test_definition_rejects_naive_datetimes() -> None:
    naive = datetime(2026, 11, 21, 12, 0)
    assert not is_aware(naive)
    with pytest.raises(DefinitionValidationError) as error:
        validate_quiz_definition(
            valid_definition(start_at=naive),
            action=DefinitionAction.DRAFT_SAVE,
        )
    assert "start_at" in {name for name, _ in error.value.issues}


def test_definition_rejects_invalid_close_order_and_publication_time_inputs() -> None:
    invalid_window = valid_definition(close_at=NOW)
    with pytest.raises(DefinitionValidationError) as error:
        validate_quiz_definition(invalid_window, action=DefinitionAction.DRAFT_SAVE)
    assert "close_at" in {name for name, _ in error.value.issues}

    complete = valid_definition()
    with pytest.raises(DefinitionValidationError) as error:
        validate_quiz_definition(
            complete,
            action=DefinitionAction.PUBLISH_NOW,
            now="not a datetime",  # type: ignore[arg-type]
        )
    assert "now" in {name for name, _ in error.value.issues}

    with pytest.raises(DefinitionValidationError) as error:
        validate_quiz_definition(QuizDefinition(), action=DefinitionAction.SCHEDULE)
    assert {"now", "title", "start_at", "close_at"}.issubset(
        {name for name, _ in error.value.issues}
    )

    with pytest.raises(DefinitionValidationError):
        validate_quiz_definition(
            complete,
            action=DefinitionAction.PUBLISH_NOW,
            now=complete.start_at - timedelta(microseconds=1),
        )


def test_publication_with_invalid_window_does_not_attempt_time_comparison() -> None:
    invalid_window = valid_definition(close_at=NOW)
    with pytest.raises(DefinitionValidationError) as error:
        validate_quiz_definition(
            invalid_window,
            action=DefinitionAction.PUBLISH_NOW,
            now=NOW,
        )
    assert "close_at" in {name for name, _ in error.value.issues}


def test_attempt_eligibility_boundaries_and_attempt_limit() -> None:
    facts = {
        "student_is_eligible": True,
        "quiz_status": QuizStatus.AVAILABLE,
        "starts_at": NOW,
        "closes_at": NOW + timedelta(minutes=10),
        "attempts_started": 0,
        "permitted_attempts": 1,
        "server_now": NOW,
    }
    require_attempt_eligibility(**facts)
    with pytest.raises(AttemptEligibilityError, match="not yet open"):
        require_attempt_eligibility(**{**facts, "server_now": NOW - timedelta(microseconds=1)})
    with pytest.raises(AttemptEligibilityError, match="closed"):
        require_attempt_eligibility(**{**facts, "server_now": facts["closes_at"]})
    with pytest.raises(AttemptEligibilityError, match="No permitted attempts"):
        require_attempt_eligibility(**{**facts, "attempts_started": 1})


def test_attempt_eligibility_fails_closed_for_invalid_supplied_facts() -> None:
    facts = {
        "student_is_eligible": True,
        "quiz_status": QuizStatus.AVAILABLE,
        "starts_at": NOW,
        "closes_at": NOW + timedelta(minutes=10),
        "attempts_started": 0,
        "permitted_attempts": 1,
        "server_now": NOW,
    }
    invalid_cases = (
        ({"server_now": datetime(2026, 11, 21, 12, 0)}, "invalid_server_time"),
        ({"student_is_eligible": False}, "student_not_eligible"),
        ({"quiz_status": QuizStatus.SCHEDULED}, "quiz_not_available"),
        ({"starts_at": None}, "availability_window_missing"),
        ({"closes_at": None}, "availability_window_missing"),
        ({"starts_at": datetime(2026, 11, 21, 12, 0)}, "invalid_availability_time"),
        ({"closes_at": datetime(2026, 11, 21, 12, 10)}, "invalid_availability_time"),
    )
    for changes, code in invalid_cases:
        with pytest.raises(AttemptEligibilityError) as error:
            require_attempt_eligibility(**{**facts, **changes})
        assert error.value.code == code

    invalid_counts = (
        {"attempts_started": True},
        {"attempts_started": -1},
        {"attempts_started": 0.5},
        {"permitted_attempts": True},
        {"permitted_attempts": 0},
        {"permitted_attempts": 1.5},
    )
    for changes in invalid_counts:
        with pytest.raises(AttemptEligibilityError) as error:
            require_attempt_eligibility(**{**facts, **changes})
        assert error.value.code == "invalid_attempt_count"


def test_deadline_is_start_plus_duration_and_boundary_is_inclusive() -> None:
    deadline = calculate_attempt_deadline(NOW, 30)
    assert deadline == NOW + timedelta(seconds=30)
    assert not deadline_reached(
        deadline_at=deadline, server_now=deadline - timedelta(microseconds=1)
    )
    assert deadline_reached(deadline_at=deadline, server_now=deadline)
    with pytest.raises(AttemptEligibilityError):
        calculate_attempt_deadline(datetime(2026, 11, 21, 12, 0), 30)


def test_deadline_rejects_invalid_duration_and_naive_comparison_times() -> None:
    for duration in (True, 0, -1, 1.5):
        with pytest.raises(AttemptEligibilityError) as error:
            calculate_attempt_deadline(NOW, duration)  # type: ignore[arg-type]
        assert error.value.code == "invalid_duration"

    with pytest.raises(AttemptEligibilityError) as error:
        deadline_reached(deadline_at=datetime(2026, 11, 21, 12, 0), server_now=NOW)
    assert error.value.code == "invalid_deadline_time"
    with pytest.raises(AttemptEligibilityError) as error:
        deadline_reached(deadline_at=NOW, server_now=datetime(2026, 11, 21, 12, 0))
    assert error.value.code == "invalid_deadline_time"


def test_mcq_scoring_and_unanswered_consistency() -> None:
    correct = UUID("00000000-0000-0000-0000-000000000001")
    incorrect = UUID("00000000-0000-0000-0000-000000000002")
    score = score_objective_response(
        question_type=QuestionType.MULTIPLE_CHOICE,
        maximum_marks=Decimal("2"),
        expected_answer=correct,
        submitted_answer=correct,
        unanswered=False,
    )
    assert (score.awarded_marks, score.is_correct, score.unanswered) == (
        Decimal("2"),
        True,
        False,
    )
    wrong = score_objective_response(
        question_type=QuestionType.MULTIPLE_CHOICE,
        maximum_marks=Decimal("2"),
        expected_answer=correct,
        submitted_answer=incorrect,
        unanswered=False,
    )
    assert wrong.awarded_marks == Decimal("0")
    with pytest.raises(DomainError, match="cannot contain an answer"):
        score_objective_response(
            question_type=QuestionType.MULTIPLE_CHOICE,
            maximum_marks=Decimal("2"),
            expected_answer=correct,
            submitted_answer=correct,
            unanswered=True,
        )
    with pytest.raises(DomainError, match="explicitly"):
        score_objective_response(
            question_type=QuestionType.MULTIPLE_CHOICE,
            maximum_marks=Decimal("2"),
            expected_answer=correct,
            submitted_answer=None,
            unanswered=False,
        )


def test_msq_is_all_or_nothing_and_true_false_scores_boolean_answers() -> None:
    first = UUID("00000000-0000-0000-0000-000000000001")
    second = UUID("00000000-0000-0000-0000-000000000002")
    expected = frozenset({first, second})
    partial = score_objective_response(
        question_type=QuestionType.MULTIPLE_SELECT,
        maximum_marks=Decimal("3"),
        expected_answer=expected,
        submitted_answer=frozenset({first}),
        unanswered=False,
    )
    assert partial.awarded_marks == Decimal("0")
    assert not partial.is_correct
    tf = score_objective_response(
        question_type=QuestionType.TRUE_FALSE,
        maximum_marks=Decimal("1"),
        expected_answer=True,
        submitted_answer=True,
        unanswered=False,
    )
    assert tf.awarded_marks == Decimal("1")


def test_negative_marking_is_policy_gated_and_fill_blank_is_unsupported() -> None:
    with pytest.raises(UnresolvedPolicyError) as error:
        score_objective_response(
            question_type=QuestionType.MULTIPLE_CHOICE,
            maximum_marks=Decimal("1"),
            expected_answer=UUID("00000000-0000-0000-0000-000000000001"),
            submitted_answer=UUID("00000000-0000-0000-0000-000000000001"),
            unanswered=False,
            negative_marking_enabled=True,
        )
    assert error.value.policy_id == "UAD-04"
    with pytest.raises(DomainError, match="no approved comparison rule"):
        score_objective_response(
            question_type=QuestionType.FILL_BLANK,
            maximum_marks=Decimal("1"),
            expected_answer="answer",  # type: ignore[arg-type]
            submitted_answer="answer",  # type: ignore[arg-type]
            unanswered=False,
        )


def test_scoring_rejects_invalid_marks_and_noncanonical_answers() -> None:
    valid_option = UUID("00000000-0000-0000-0000-000000000001")
    for marks in (1.0, Decimal("0"), Decimal("-1"), Decimal("Infinity")):
        with pytest.raises(DomainError, match="Maximum marks"):
            score_objective_response(
                question_type=QuestionType.MULTIPLE_CHOICE,
                maximum_marks=marks,  # type: ignore[arg-type]
                expected_answer=valid_option,
                submitted_answer=valid_option,
                unanswered=False,
            )

    invalid_answers = (
        (QuestionType.MULTIPLE_CHOICE, True, valid_option),
        (QuestionType.TRUE_FALSE, 1, True),
        (QuestionType.MULTIPLE_SELECT, {valid_option}, frozenset({valid_option})),
        (QuestionType.MULTIPLE_SELECT, frozenset({"bad-id"}), frozenset({valid_option})),
    )
    for question_type, expected, submitted in invalid_answers:
        with pytest.raises(DomainError, match=r"canonical|booleans|UUID"):
            score_objective_response(
                question_type=question_type,
                maximum_marks=Decimal("1"),
                expected_answer=expected,  # type: ignore[arg-type]
                submitted_answer=submitted,  # type: ignore[arg-type]
                unanswered=False,
            )

    with pytest.raises(DomainError, match="Subjective question types"):
        score_objective_response(
            question_type=QuestionType.SHORT_ANSWER,
            maximum_marks=Decimal("1"),
            expected_answer=valid_option,
            submitted_answer=valid_option,
            unanswered=False,
        )

    blank = score_objective_response(
        question_type=QuestionType.MULTIPLE_CHOICE,
        maximum_marks=Decimal("1"),
        expected_answer=valid_option,
        submitted_answer=None,
        unanswered=True,
    )
    assert blank.awarded_marks == Decimal("0")
    assert blank.unanswered and not blank.is_correct
