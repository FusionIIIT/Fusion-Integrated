"""Privilege escalation tests: a principal without permission gets 403/404."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.models import Assignment, CourseMaterial

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def material():
    return CourseMaterial.objects.create(
        course_id=1, user_id=1, title="Syllabus", material_type="note",
        content="Welcome", status="published",
    )


@pytest.fixture
def assignment():
    from django.utils import timezone
    return Assignment.objects.create(
        course_id=1, user_id=1, title="HW1",
        due_at=timezone.now(), submission_type="file", points_possible=10,
    )


def test_student_cannot_create_material(stub_iam, material):
    c = _client(stub_iam, user_id=100, modules=("lms",),
                permissions=("lms.course.view", "lms.material.view"))
    resp = c.post("/api/v1/lms/courses/1/materials/", {
        "title": "X", "material_type": "note", "content": "y",
    }, format="json")
    assert resp.status_code in (403, 405)


def test_student_cannot_create_assignment(stub_iam, assignment):
    c = _client(stub_iam, user_id=100, modules=("lms",),
                permissions=("lms.course.view", "lms.assignment.view"))
    resp = c.post("/api/v1/lms/courses/1/assignments/", {
        "title": "X", "due_at": "2026-12-01T23:59:00Z",
        "submission_type": "file", "points_possible": 10,
    }, format="json")
    assert resp.status_code in (403, 405)


def test_no_module_grant_returns_403(stub_iam):
    c = _client(stub_iam, user_id=100, modules=(),
                permissions=("lms.course.view",))
    resp = c.get("/api/v1/lms/courses/1/")
    assert resp.status_code in (403, 404)
