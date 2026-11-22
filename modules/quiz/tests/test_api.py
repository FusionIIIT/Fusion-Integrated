from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.quiz.models import QuizQuestion
from modules.quiz.services.quiz_service import create_quiz, publish_quiz


@pytest.fixture
def sample_quiz(db):
    quiz = create_quiz(
        course_id=101,
        title="Intro to Computing",
        instructions="Read instructions",
        duration_minutes=30,
        max_attempts=1,
        created_by_user_id=1001,
    )
    QuizQuestion.objects.create(
        quiz=quiz,
        question_text="What is RAM?",
        question_type="MCQ",
        marks=Decimal("5.00"),
        correct=["Random Access Memory"],
        position=1,
    )
    publish_quiz(quiz.pk, 1001)
    return quiz


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.mark.django_db
def test_quiz_list_authorized_faculty(stub_iam, sample_quiz):
    c = _client(
        stub_iam,
        user_id=1001,
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        modules=("quiz",),
        permissions=("quiz.manage", "quiz.quiz.view"),
    )
    resp = c.get("/api/v1/quiz/quizzes/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


@pytest.mark.django_db
def test_quiz_list_negative_twin_no_module_grant(stub_iam, sample_quiz):
    c = _client(
        stub_iam,
        user_id=1001,
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        modules=(),  # No quiz module grant!
        permissions=("quiz.manage", "quiz.quiz.view"),
    )
    resp = c.get("/api/v1/quiz/quizzes/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_quiz_list_negative_twin_no_permission(stub_iam, sample_quiz):
    c = _client(
        stub_iam,
        user_id=1001,
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        modules=("quiz",),
        permissions=(),  # No permission code!
    )
    resp = c.get("/api/v1/quiz/quizzes/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_quiz_list_invalid_query_param_gives_400(stub_iam, sample_quiz):
    c = _client(
        stub_iam,
        user_id=1001,
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        modules=("quiz",),
        permissions=("quiz.manage", "quiz.quiz.view"),
    )
    resp = c.get("/api/v1/quiz/quizzes/?course_id=abc")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_quiz_detail_scoping_unpermitted_row_gives_404(stub_iam, sample_quiz):
    # Other faculty trying to view quiz
    c = _client(
        stub_iam,
        user_id=9999,  # Different user
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        modules=("quiz",),
        permissions=("quiz.manage", "quiz.quiz.view"),
    )
    resp = c.get(f"/api/v1/quiz/quizzes/{sample_quiz.pk}/")
    assert resp.status_code == 404
