"""Quiz API tests; database-backed tests require the approved local services."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.quiz.models import (
    Attempt,
    AttemptQuestion,
    Question,
    QuestionOption,
    Quiz,
    QuizResult,
    Response,
)

pytestmark = pytest.mark.django_db


def client_for(stub_iam, *, user_id=501, kind="faculty", permissions=()):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            modules=("quiz",),
            permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token quiz-test-token")
    return client


def make_quiz(*, course_id=77, status_value="draft") -> Quiz:
    return Quiz.objects.create(
        course_id=course_id,
        created_by_user_id=501,
        title="Assessment",
        description="Description",
        instructions="Instructions",
        duration_seconds=600,
        maximum_marks=Decimal("10"),
        passing_marks=Decimal("5"),
        permitted_attempts=2,
        status=status_value,
        start_at=timezone.now() - timedelta(minutes=1),
        close_at=timezone.now() + timedelta(hours=1),
    )


def make_attempt(*, quiz: Quiz, student_user_id=1001, attempt_number=1) -> Attempt:
    now = timezone.now()
    return Attempt.objects.create(
        quiz=quiz,
        student_user_id=student_user_id,
        attempt_number=attempt_number,
        started_at=now,
        deadline_at=now + timedelta(minutes=10),
    )


def test_authentication_and_student_professor_role_separation(stub_iam):
    unauthenticated = APIClient().get("/api/v1/quiz/quizzes")
    assert unauthenticated.status_code == 401

    student = client_for(
        stub_iam,
        user_id=1001,
        kind="student",
        permissions=("quiz.quiz.create",),
    )
    response = student.post(
        "/api/v1/quiz/quizzes",
        {"title": "Attempted authoring", "course_id": 77},
        format="json",
    )
    assert response.status_code == 403

    ungranted_professor = client_for(stub_iam, permissions=())
    assert (
        ungranted_professor.post(
            "/api/v1/quiz/quizzes",
            {"title": "No permission", "course_id": 77},
            format="json",
        ).status_code
        == 403
    )


def test_professor_course_reads_fail_closed_without_scope_provider(stub_iam):
    professor = client_for(stub_iam, permissions=("quiz.quiz.view",))
    response = professor.get("/api/v1/quiz/quizzes")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "academic_authorization_unavailable"


def test_professor_quiz_scope_and_create_course_isolation(stub_iam, monkeypatch):
    from modules.quiz.api import views

    monkeypatch.setattr(views, "_trusted_course_ids", lambda _principal: [77])
    in_scope = make_quiz(course_id=77)
    out_of_scope = make_quiz(course_id=88)
    professor = client_for(
        stub_iam,
        permissions=("quiz.quiz.view", "quiz.quiz.create"),
    )

    listing = professor.get("/api/v1/quiz/quizzes")
    assert listing.status_code == 200
    assert [row["public_id"] for row in listing.json()["results"]] == [str(in_scope.public_id)]
    assert professor.get(f"/api/v1/quiz/quizzes/{out_of_scope.public_id}").status_code == 404
    denied_create = professor.post(
        "/api/v1/quiz/quizzes",
        {"title": "Out of scope", "course_id": 88},
        format="json",
    )
    assert denied_create.status_code == 403


def test_professor_can_create_and_update_a_draft(stub_iam, monkeypatch):
    from modules.quiz.api import views

    monkeypatch.setattr(views, "_trusted_course_ids", lambda _principal: [77])
    professor = client_for(
        stub_iam,
        permissions=("quiz.quiz.create", "quiz.quiz.update"),
    )
    created = professor.post(
        "/api/v1/quiz/quizzes",
        {
            "title": "Draft one",
            "course_id": 77,
            "description": "Keep this",
            "instructions": "Keep these",
        },
        format="json",
    )
    assert created.status_code == 201
    public_id = created.json()["public_id"]

    updated = professor.put(
        f"/api/v1/quiz/quizzes/{public_id}",
        {
            "title": "Draft revised",
            "course_id": 77,
            "duration_seconds": None,
            "maximum_marks": None,
            "passing_marks": None,
            "permitted_attempts": None,
            "start_at": None,
            "close_at": None,
        },
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Draft revised"
    quiz = Quiz.objects.get(public_id=public_id)
    assert quiz.description == "Keep this"
    assert quiz.instructions == "Keep these"


def test_publish_validation_uses_domain_and_maps_status(stub_iam, monkeypatch):
    from modules.quiz.api import views

    monkeypatch.setattr(views, "_trusted_course_ids", lambda _principal: [77])
    quiz = make_quiz()
    quiz.duration_seconds = None
    quiz.save(update_fields=["duration_seconds"])
    professor = client_for(stub_iam, permissions=("quiz.quiz.publish",))

    response = professor.post(
        f"/api/v1/quiz/quizzes/{quiz.public_id}/publish",
        {"action": "publish_now"},
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_quiz_definition"


def test_question_bank_reads_are_creator_scoped_and_students_are_denied(stub_iam):
    own = Question.objects.create(
        created_by_user_id=1001,
        question_type="multiple_choice",
        prompt="Private prompt",
        marks=Decimal("1"),
        answer_key={"correct": "private"},
        reference_answer="private reference",
        evaluation_criteria={"rubric": "private"},
    )
    Question.objects.create(
        created_by_user_id=2002,
        question_type="multiple_choice",
        prompt="Peer question",
        marks=Decimal("1"),
    )
    student = client_for(
        stub_iam,
        user_id=1001,
        kind="student",
        permissions=("quiz.question.view",),
    )
    assert student.get("/api/v1/quiz/questions").status_code == 403

    professor = client_for(
        stub_iam,
        user_id=1001,
        permissions=("quiz.question.view",),
    )
    response = professor.get("/api/v1/quiz/questions")
    assert response.status_code == 200
    rows = response.json()["results"]
    assert [row["public_id"] for row in rows] == [str(own.public_id)]
    assert rows[0]["answer_key"] == {"correct": "private"}


def test_student_eligibility_fails_closed_without_academic_provider(stub_iam):
    student = client_for(
        stub_iam,
        user_id=1001,
        kind="student",
        permissions=("quiz.quiz.view",),
    )
    response = student.get("/api/v1/quiz/eligible-quizzes")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "academic_authorization_unavailable"


def test_student_eligible_quiz_list_uses_only_trusted_ids(stub_iam, monkeypatch):
    from modules.quiz.api import views

    quiz = make_quiz(status_value="available")
    monkeypatch.setattr(
        views,
        "_trusted_eligible_quiz_ids",
        lambda _principal: [quiz.public_id],
    )
    student = client_for(
        stub_iam,
        user_id=1001,
        kind="student",
        permissions=("quiz.quiz.view",),
    )

    response = student.get("/api/v1/quiz/eligible-quizzes")
    assert response.status_code == 200
    rows = response.json()["results"]
    assert [row["public_id"] for row in rows] == [str(quiz.public_id)]
    assert "answer_key" not in rows[0]


def test_student_attempt_presentation_and_response_submission_are_owner_scoped(
    stub_iam,
):
    quiz = make_quiz(status_value="available")
    attempt = make_attempt(quiz=quiz)
    peer_attempt = make_attempt(quiz=quiz, student_user_id=2002)
    question = Question.objects.create(
        created_by_user_id=501,
        question_type="multiple_choice",
        prompt="Choose one.",
        marks=Decimal("2"),
        answer_key={"correct": "hidden"},
        reference_answer="hidden",
        evaluation_criteria={"rubric": "hidden"},
    )
    option = QuestionOption.objects.create(
        question=question,
        text="Option A",
        is_correct=True,
        position=1,
    )
    item = AttemptQuestion.objects.create(
        attempt=attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[str(option.option_key)],
        marks_at_start=Decimal("2"),
    )
    AttemptQuestion.objects.create(
        attempt=peer_attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[str(option.option_key)],
        marks_at_start=Decimal("2"),
    )
    student = client_for(
        stub_iam,
        user_id=1001,
        kind="student",
        permissions=(
            "quiz.attempt.view",
            "quiz.response.update",
            "quiz.attempt.update",
        ),
    )

    foreign = student.get(f"/api/v1/quiz/attempts/{peer_attempt.pk}")
    assert foreign.status_code == 404
    detail = student.get(f"/api/v1/quiz/attempts/{attempt.pk}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["items"][0]["options"][0]["option_key"] == str(option.option_key)
    for private_field in ("answer_key", "is_correct", "reference_answer", "evaluation_criteria"):
        assert private_field not in str(body)

    saved = student.put(
        f"/api/v1/quiz/attempts/{attempt.pk}/responses/{item.pk}",
        {"answer_payload": {"option_key": str(option.option_key)}, "expected_revision": 0},
        format="json",
    )
    assert saved.status_code == 200
    assert saved.json()["revision"] == 1
    assert "answer_key" not in saved.json()

    submitted = student.post(
        f"/api/v1/quiz/attempts/{attempt.pk}/submit",
        {"confirmed": True},
        format="json",
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert Response.objects.filter(attempt_question=item).exists()


def test_only_own_released_results_are_visible(stub_iam):
    quiz = make_quiz()
    own_attempt = make_attempt(quiz=quiz)
    foreign_attempt = make_attempt(quiz=quiz, student_user_id=2002)
    own_result = QuizResult.objects.create(
        attempt=own_attempt,
        status="released",
        total_marks=Decimal("10"),
        marks_obtained=Decimal("7"),
        percentage=Decimal("70"),
        correct_count=7,
        incorrect_count=3,
        unanswered_count=0,
        passed=True,
        released_by_user_id=501,
        released_at=timezone.now(),
    )
    own_pending_attempt = make_attempt(quiz=quiz, student_user_id=1001, attempt_number=2)
    own_pending_result = QuizResult.objects.create(attempt=own_pending_attempt)
    foreign_result = QuizResult.objects.create(
        attempt=foreign_attempt,
        status="released",
        released_by_user_id=501,
        released_at=timezone.now(),
    )
    student = client_for(
        stub_iam,
        user_id=1001,
        kind="student",
        permissions=("quiz.result.view",),
    )

    own = student.get(f"/api/v1/quiz/results/{own_result.pk}")
    assert own.status_code == 200
    assert own.json()["marks_obtained"] == "7.00"
    assert student.get(f"/api/v1/quiz/results/{own_pending_result.pk}").status_code == 404
    assert student.get(f"/api/v1/quiz/results/{foreign_result.pk}").status_code == 404


def test_api_rejects_invalid_request_payloads(stub_iam, monkeypatch):
    from modules.quiz.api import views

    monkeypatch.setattr(views, "_trusted_course_ids", lambda _principal: [77])
    professor = client_for(stub_iam, permissions=("quiz.quiz.create",))
    response = professor.post(
        "/api/v1/quiz/quizzes",
        {"course_id": 77, "title": ""},
        format="json",
    )
    assert response.status_code == 400
