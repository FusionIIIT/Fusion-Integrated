"""Scoping isolation: person A must not see person B's rows."""
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
def two_materials():
    CourseMaterial.objects.create(course_id=1, user_id=1, title="M1", material_type="note", content="a", status="published")
    CourseMaterial.objects.create(course_id=2, user_id=2, title="M2", material_type="note", content="b", status="published")


def test_materials_scoped_by_course(stub_iam, two_materials):
    c = _client(stub_iam, user_id=100, modules=("lms",),
                permissions=("lms.material.view",))
    resp = c.get("/api/v1/lms/courses/1/materials/")
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict):
        data = data.get("results", [])
    titles = [m["title"] for m in data]
    assert "M1" in titles
    assert "M2" not in titles


@pytest.fixture
def two_assignments():
    from django.utils import timezone
    Assignment.objects.create(course_id=1, user_id=1, title="A1", due_at=timezone.now(), submission_type="file", points_possible=10, status="available")
    Assignment.objects.create(course_id=2, user_id=2, title="A2", due_at=timezone.now(), submission_type="file", points_possible=10, status="available")


def test_assignments_scoped_by_course(stub_iam, two_assignments):
    c = _client(stub_iam, user_id=100, modules=("lms",),
                permissions=("lms.assignment.view",))
    resp = c.get("/api/v1/lms/courses/1/assignments/")
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict):
        data = data.get("results", [])
    titles = [a["title"] for a in data]
    assert "A1" in titles
    assert "A2" not in titles
