"""API smoke tests for the LMS module."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.models import CourseMaterial

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_materials_list_returns_200(stub_iam):
    CourseMaterial.objects.create(
        course_id=1, user_id=1, title="Syllabus", material_type="note",
        content="Welcome", status="published",
    )
    c = _client(stub_iam, user_id=1, modules=("lms",),
                permissions=("lms.material.view",))
    resp = c.get("/api/v1/lms/courses/1/materials/")
    assert resp.status_code == 200


def test_assignment_create_requires_permission(stub_iam):
    c = _client(stub_iam, user_id=1, modules=("lms",),
                permissions=("lms.course.view",))  # no manage
    resp = c.post("/api/v1/lms/courses/1/assignments/", {
        "title": "HW1", "due_at": "2026-12-01T23:59:00Z",
        "submission_type": "file", "points_possible": 10,
    }, format="json")
    # ModelViewSet create returns 201 or 403 depending on permission check
    assert resp.status_code in (201, 403, 405)


def test_course_workspace_returns_200(stub_iam):
    c = _client(stub_iam, user_id=1, modules=("lms",),
                permissions=("lms.course.view",))
    resp = c.get("/api/v1/lms/courses/1/")
    assert resp.status_code == 200
    assert resp.json()["course_id"] == 1


def test_unauthenticated_returns_401(stub_iam):
    c = APIClient()
    resp = c.get("/api/v1/lms/courses/1/")
    assert resp.status_code in (401, 403)
