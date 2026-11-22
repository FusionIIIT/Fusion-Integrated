from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.quiz.models import (
    QuizResult,
    ResponseEvaluation,
)
from modules.quiz.services.attempt_service import (
    record_tab_violation,
    save_response,
    start_quiz_attempt,
    submit_quiz_attempt,
)
from modules.quiz.services.evaluation_service import (
    grade_subjective_response,
    release_quiz_results,
)
from modules.quiz.services.question_service import add_quiz_question
from modules.quiz.services.quiz_service import create_quiz, publish_quiz, update_quiz


@pytest.mark.django_db
def test_quiz_lifecycle_service():
    quiz = create_quiz(
        course_id=101,
        title="Python Data Structures",
        instructions="Complete within time",
        duration_minutes=45,
        max_attempts=1,
        created_by_user_id=501,
    )
    assert quiz.status == "DRAFT"
    assert quiz.settings is not None

    # Add question so it can be published
    q = add_quiz_question(
        quiz_id=quiz.pk,
        user_id=501,
        question_text="What is a set?",
        question_type="MCQ",
        marks=Decimal("5.00"),
        correct=["An unordered collection of unique elements"],
        options=[
            {"option_id": "A", "option_text": "An ordered list"},
            {"option_id": "B", "option_text": "An unordered collection of unique elements"},
        ],
    )
    assert q.position == 1

    # Publish
    published = publish_quiz(quiz.pk, 501)
    assert published.status == "AVAILABLE"

    # Cannot edit after publish
    with pytest.raises(ConflictError):
        update_quiz(quiz.pk, 501, title="New Title")


@pytest.mark.django_db
def test_attempt_and_evaluation_service():
    quiz = create_quiz(
        course_id=102,
        title="Algorithms Quiz",
        instructions="Good luck",
        duration_minutes=30,
        max_attempts=2,
        created_by_user_id=501,
    )
    q1 = add_quiz_question(
        quiz_id=quiz.pk,
        user_id=501,
        question_text="2 + 2 = ?",
        question_type="MCQ",
        marks=Decimal("2.00"),
        correct=["4"],
    )
    q2 = add_quiz_question(
        quiz_id=quiz.pk,
        user_id=501,
        question_text="Explain recursion.",
        question_type="SHORT",
        marks=Decimal("8.00"),
        correct=[],
    )
    publish_quiz(quiz.pk, 501)

    # Student starts attempt
    attempt = start_quiz_attempt(quiz.pk, student_id=2001)
    assert attempt.status == "STARTED"

    # Save answers
    save_response(attempt.pk, student_id=2001, question_id=q1.pk, answer="4")
    save_response(
        attempt.pk, student_id=2001, question_id=q2.pk, answer="A function calling itself."
    )

    # Tab violations
    v_res = record_tab_violation(attempt.pk, student_id=2001)
    assert v_res["tab_violations"] == 1

    # Submit attempt
    submitted = submit_quiz_attempt(attempt.pk, student_id=2001)
    assert submitted.status == "SUBMITTED"

    # Result state is PARTIALLY_EVALUATED because q2 is subjective
    res = QuizResult.objects.get(attempt=submitted)
    assert res.status == "PARTIALLY_EVALUATED"

    # Faculty grades q2
    ev = ResponseEvaluation.objects.get(response__attempt=submitted, response__question=q2)
    graded_ev = grade_subjective_response(
        ev.pk, faculty_user_id=501, marks=Decimal("7.00"), feedback="Good explanation."
    )
    assert graded_ev.status == "FINAL"

    # Re-check result is now EVALUATED
    res.refresh_from_db()
    assert res.status == "EVALUATED"
    assert res.marks_obtained == Decimal("9.00")

    # Release result
    released_count = release_quiz_results(quiz.pk, faculty_user_id=501)
    assert released_count == 1
    res.refresh_from_db()
    assert res.status == "RELEASED"
