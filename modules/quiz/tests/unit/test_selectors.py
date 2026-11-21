"""Database-backed tests for Quiz selector scoping and projections."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.quiz.models import (
    Attempt,
    AttemptQuestion,
    Question,
    QuestionOption,
    Quiz,
    QuizQuestion,
    QuizResult,
    Response,
)
from modules.quiz.selectors import (
    attempt_for_student,
    attempts_for_courses,
    attempts_for_student,
    eligible_quizzes_for_student,
    question_bank_for_creator,
    quiz_for_courses,
    quiz_prestart_for_student,
    quizzes_for_courses,
    released_results_for_student,
    results_for_courses,
    student_attempt_presentation_rows,
    student_result_rows,
)

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def make_quiz(*, course_id: int, **overrides: object) -> Quiz:
    values: dict[str, object] = {
        "course_id": course_id,
        "created_by_user_id": 900,
        "title": f"Quiz for course {course_id}",
        "duration_seconds": 600,
        "maximum_marks": Decimal("10"),
        "passing_marks": Decimal("5"),
        "permitted_attempts": 2,
    }
    values.update(overrides)
    return Quiz.objects.create(**values)  # type: ignore[arg-type]


def make_attempt(*, quiz: Quiz, student_user_id: int, **overrides: object) -> Attempt:
    values: dict[str, object] = {
        "quiz": quiz,
        "student_user_id": student_user_id,
        "attempt_number": 1,
        "started_at": NOW - timedelta(minutes=1),
        "deadline_at": NOW + timedelta(minutes=9),
    }
    values.update(overrides)
    return Attempt.objects.create(**values)  # type: ignore[arg-type]


def test_professor_quiz_queries_are_narrowed_to_supplied_course_scope() -> None:
    in_scope = make_quiz(course_id=10)
    out_of_scope = make_quiz(course_id=20)

    assert list(quizzes_for_courses([10])) == [in_scope]
    assert list(quiz_for_courses(public_id=out_of_scope.public_id, course_ids=[10])) == []


def test_student_quiz_list_uses_eligibility_and_annotates_counts() -> None:
    available = make_quiz(
        course_id=10,
        status="available",
        start_at=NOW - timedelta(minutes=1),
        close_at=NOW + timedelta(hours=1),
    )
    scheduled = make_quiz(
        course_id=10,
        status="scheduled",
        start_at=NOW + timedelta(hours=1),
        close_at=NOW + timedelta(hours=2),
    )
    closed = make_quiz(
        course_id=10,
        status="closed",
        start_at=NOW - timedelta(hours=2),
        close_at=NOW - timedelta(hours=1),
    )
    not_eligible = make_quiz(
        course_id=10,
        status="available",
        start_at=NOW - timedelta(minutes=1),
        close_at=NOW + timedelta(hours=1),
    )
    question_a = Question.objects.create(
        created_by_user_id=900,
        question_type="multiple_choice",
        prompt="Question A",
        marks=Decimal("1"),
    )
    question_b = Question.objects.create(
        created_by_user_id=900,
        question_type="true_false",
        prompt="Question B",
        marks=Decimal("1"),
    )
    QuizQuestion.objects.create(quiz=available, question=question_a, position=1)
    QuizQuestion.objects.create(quiz=available, question=question_b, position=2)
    make_attempt(quiz=available, student_user_id=101)
    make_attempt(quiz=available, student_user_id=202)

    rows = list(
        eligible_quizzes_for_student(
            eligible_quiz_ids=[available.public_id, scheduled.public_id, closed.public_id],
            student_user_id=101,
            server_now=NOW,
        )
    )
    by_id = {row.public_id: row for row in rows}
    assert set(by_id) == {available.public_id, scheduled.public_id}
    assert by_id[available.public_id].question_count == 2
    assert by_id[available.public_id].attempts_started == 1
    assert (
        list(
            quiz_prestart_for_student(
                public_id=not_eligible.public_id,
                eligible_quiz_ids=[available.public_id],
                student_user_id=101,
                server_now=NOW,
            )
        )
        == []
    )


def test_scheduled_quiz_remains_visible_at_start_until_close_without_transition() -> None:
    starting = make_quiz(
        course_id=10,
        status="scheduled",
        start_at=NOW,
        close_at=NOW + timedelta(hours=1),
    )
    closing = make_quiz(
        course_id=10,
        status="scheduled",
        start_at=NOW - timedelta(hours=1),
        close_at=NOW,
    )

    rows = list(
        eligible_quizzes_for_student(
            eligible_quiz_ids=[starting.public_id, closing.public_id],
            student_user_id=101,
            server_now=NOW,
        )
    )
    assert [row.public_id for row in rows] == [starting.public_id]
    assert rows[0].status == "scheduled"


def test_empty_scopes_fail_closed_and_question_bank_no_match_is_empty() -> None:
    assert list(quizzes_for_courses([])) == []
    assert list(attempts_for_courses([])) == []
    assert list(results_for_courses([])) == []
    assert (
        list(
            eligible_quizzes_for_student(
                eligible_quiz_ids=[],
                student_user_id=101,
                server_now=NOW,
            )
        )
        == []
    )
    assert list(question_bank_for_creator(creator_user_id=999)) == []


def test_student_attempt_and_presentation_are_owner_scoped_and_key_free() -> None:
    quiz = make_quiz(course_id=10)
    owned = make_attempt(quiz=quiz, student_user_id=101)
    foreign = make_attempt(quiz=quiz, student_user_id=202)
    question = Question.objects.create(
        created_by_user_id=900,
        question_type="multiple_choice",
        prompt="Visible prompt",
        marks=Decimal("2"),
        answer_key={"private": "secret-key"},
        reference_answer="private reference",
        evaluation_criteria={"private": "rubric"},
    )
    option = QuestionOption.objects.create(
        question=question,
        text="Visible option",
        is_correct=True,
        position=1,
    )
    second_option = QuestionOption.objects.create(
        question=question,
        text="Second visible option",
        is_correct=False,
        position=2,
    )
    item = AttemptQuestion.objects.create(
        attempt=owned,
        question=question,
        display_order=1,
        displayed_option_keys=[str(second_option.option_key), str(option.option_key)],
        marks_at_start=Decimal("2"),
    )
    Response.objects.create(
        attempt_question=item,
        answer_payload={"selected": str(option.option_key)},
        saved_at=NOW,
    )

    assert list(attempts_for_student(101)) == [owned]
    assert list(attempt_for_student(attempt_id=foreign.pk, student_user_id=101)) == []
    assert {row.pk for row in attempts_for_courses([10])} == {owned.pk, foreign.pk}
    rows = list(student_attempt_presentation_rows(attempt_id=owned.pk, student_user_id=101))
    assert len(rows) == 2
    row = rows[0]
    assert row["question__prompt"] == "Visible prompt"
    assert row["displayed_option_keys"] == [
        str(second_option.option_key),
        str(option.option_key),
    ]
    rows_by_option_id = {
        str(presentation["question__options__option_key"]): presentation for presentation in rows
    }
    reconstructed_order = [
        rows_by_option_id[option_key] for option_key in row["displayed_option_keys"]
    ]
    assert [presentation["question__options__text"] for presentation in reconstructed_order] == [
        "Second visible option",
        "Visible option",
    ]
    assert "question__options__position" not in row
    assert "question__options__is_correct" not in row
    assert "question__answer_key" not in row
    assert "question__reference_answer" not in row
    assert "question__evaluation_criteria" not in row
    assert "private" not in repr(row)
    assert list(student_attempt_presentation_rows(attempt_id=foreign.pk, student_user_id=101)) == []


def test_subjective_question_without_options_has_null_option_fields() -> None:
    quiz = make_quiz(course_id=10)
    attempt = make_attempt(quiz=quiz, student_user_id=101)
    question = Question.objects.create(
        created_by_user_id=900,
        question_type="short_answer",
        prompt="Explain the concept.",
        marks=Decimal("2"),
    )
    AttemptQuestion.objects.create(
        attempt=attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[],
        marks_at_start=Decimal("2"),
    )

    rows = list(student_attempt_presentation_rows(attempt_id=attempt.pk, student_user_id=101))
    assert len(rows) == 1
    assert rows[0]["question__options__option_key"] is None
    assert rows[0]["question__options__text"] is None


def test_new_attempt_question_without_response_has_null_response_fields() -> None:
    quiz = make_quiz(course_id=10)
    attempt = make_attempt(quiz=quiz, student_user_id=101)
    question = Question.objects.create(
        created_by_user_id=900,
        question_type="true_false",
        prompt="A statement.",
        marks=Decimal("1"),
    )
    AttemptQuestion.objects.create(
        attempt=attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[],
        marks_at_start=Decimal("1"),
    )

    rows = list(student_attempt_presentation_rows(attempt_id=attempt.pk, student_user_id=101))
    assert len(rows) == 1
    assert rows[0]["response__answer_payload"] is None
    assert rows[0]["response__revision"] is None
    assert rows[0]["response__saved_at"] is None


def test_student_results_require_ownership_and_release() -> None:
    quiz = make_quiz(course_id=10)
    owned = make_attempt(quiz=quiz, student_user_id=101)
    foreign = make_attempt(quiz=quiz, student_user_id=202)
    released = QuizResult.objects.create(
        attempt=owned,
        status="released",
        total_marks=Decimal("10"),
        marks_obtained=Decimal("8"),
        percentage=Decimal("80"),
        passed=True,
        released_by_user_id=900,
        released_at=NOW,
    )
    unreleased = QuizResult.objects.create(
        attempt=make_attempt(quiz=quiz, student_user_id=101, attempt_number=2)
    )
    other_student_result = QuizResult.objects.create(
        attempt=foreign,
        status="released",
        released_by_user_id=900,
        released_at=NOW,
    )

    rows = list(released_results_for_student(101))
    assert [row["id"] for row in rows] == [released.pk]
    assert list(student_result_rows(student_user_id=101, result_id=unreleased.pk)) == []
    assert other_student_result.pk not in {row["id"] for row in rows}
    assert "answer_key" not in rows[0]
    assert {row.pk for row in results_for_courses([10])} == {
        released.pk,
        unreleased.pk,
        other_student_result.pk,
    }
    assert list(results_for_courses([999])) == []


def test_question_bank_filters_creator_and_prefetches_options(django_assert_num_queries) -> None:
    own = Question.objects.create(
        created_by_user_id=101,
        subject_id=7,
        question_type="multiple_choice",
        prompt="Owned question",
        marks=Decimal("1"),
        topic="Algebra",
        difficulty="easy",
    )
    QuestionOption.objects.create(question=own, text="A", is_correct=True, position=1)
    Question.objects.create(
        created_by_user_id=202,
        subject_id=7,
        question_type="multiple_choice",
        prompt="Other creator question",
        marks=Decimal("1"),
        topic="Algebra",
        difficulty="easy",
    )
    Question.objects.create(
        created_by_user_id=101,
        subject_id=8,
        question_type="short_answer",
        prompt="Different subject question",
        marks=Decimal("1"),
    )

    queryset = question_bank_for_creator(
        creator_user_id=101,
        subject_id=7,
        topic="alg",
        difficulty="easy",
        question_type="multiple_choice",
    )
    with django_assert_num_queries(2):
        results = list(queryset)
        options = list(results[0].options.all())
    assert [question.pk for question in results] == [own.pk]
    assert len(options) == 1
    assert options[0].is_correct is True
