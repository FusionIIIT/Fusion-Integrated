"""Journey tests: one per live use case's main success scenario, driven through HTTP."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.models import Assignment

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


# UC-LMS-001: Access Course Workspace
def test_uc001_access_course_workspace(stub_iam):
    c = _client(stub_iam, user_id=1, modules=("lms",),
                permissions=("lms.course.view",))
    resp = c.get("/api/v1/lms/courses/1/")
    assert resp.status_code == 200
    assert resp.json()["course_id"] == 1


# UC-LMS-003 + UC-LMS-004: Manage and view course materials
def test_uc003_uc004_materials_lifecycle(stub_iam):
    # Faculty creates a material
    fc = _client(stub_iam, user_id=1, modules=("lms",),
                 permissions=("lms.course.view", "lms.material.manage", "lms.material.view"))
    resp = fc.post("/api/v1/lms/courses/1/materials/", {
        "title": "Syllabus", "material_type": "note", "content": "Welcome", "status": "published",
    }, format="json")
    assert resp.status_code == 201

    # Student views published materials
    sc = _client(stub_iam, user_id=100, modules=("lms",),
                 permissions=("lms.course.view", "lms.material.view"))
    resp = sc.get("/api/v1/lms/courses/1/materials/")
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict):
        data = data.get("results", [])
    assert any(m["title"] == "Syllabus" for m in data)


# UC-LMS-005 + UC-LMS-006: Post and view announcements
def test_uc005_uc006_announcements(stub_iam):
    fc = _client(stub_iam, user_id=1, modules=("lms",),
                 permissions=("lms.course.view", "lms.announcement.create", "lms.announcement.view"))
    resp = fc.post("/api/v1/lms/courses/1/announcements/", {
        "content": "Welcome to the course!", "is_pinned": False,
    }, format="json")
    assert resp.status_code == 201

    sc = _client(stub_iam, user_id=100, modules=("lms",),
                 permissions=("lms.course.view", "lms.announcement.view"))
    resp = sc.get("/api/v1/lms/courses/1/announcements/")
    assert resp.status_code == 200
    data = resp.json()
    if isinstance(data, dict):
        data = data.get("results", [])
    assert any("Welcome" in a["content"] for a in data)


# UC-LMS-007 + UC-LMS-008 + UC-LMS-009: Create, publish, view assignment
def test_uc007_uc008_uc009_assignment_lifecycle(stub_iam):
    fc = _client(stub_iam, user_id=1, modules=("lms",),
                 permissions=("lms.course.view", "lms.assignment.manage", "lms.assignment.view"))
    resp = fc.post("/api/v1/lms/courses/1/assignments/", {
        "title": "HW1", "instructions": "Do the thing",
        "due_at": "2026-12-01T23:59:00Z", "submission_type": "text",
        "points_possible": 10,
    }, format="json")
    assert resp.status_code == 201
    aid = resp.json()["id"]

    # Publish
    resp = fc.post(f"/api/v1/lms/courses/1/assignments/{aid}/publish/", {})
    assert resp.status_code in (200, 201)

    # Student views published assignment
    sc = _client(stub_iam, user_id=100, modules=("lms",),
                 permissions=("lms.course.view", "lms.assignment.view"))
    resp = sc.get(f"/api/v1/lms/courses/1/assignments/{aid}/")
    assert resp.status_code == 200


# UC-LMS-010 + UC-LMS-011: Submit and view submission history
def test_uc010_uc011_submit_and_view(stub_iam):
    a = Assignment.objects.create(
        course_id=1, user_id=1, title="HW2", due_at=timezone.now(),
        submission_type="text", points_possible=10, status="available",
    )
    sc = _client(stub_iam, user_id=100, modules=("lms",),
                 permissions=("lms.course.view", "lms.submission.create", "lms.submission.view_own"))
    resp = sc.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submit/", {
        "submission_type": "text", "content": "My answer",
    }, format="json")
    assert resp.status_code == 201

    resp = sc.get(f"/api/v1/lms/courses/1/assignments/{a.id}/my-submission/")
    assert resp.status_code == 200


# UC-LMS-012 + UC-LMS-013 + UC-LMS-014: Grade, release, view
def test_uc012_uc013_uc014_grade_release_view(stub_iam):
    a = Assignment.objects.create(
        course_id=1, user_id=1, title="HW3", due_at=timezone.now(),
        submission_type="text", points_possible=10, status="available",
    )
    from modules.lms.models import Submission
    s = Submission.objects.create(
        assignment=a, user_id=100, submission_type="text",
        content="Answer", status="submitted",
    )

    # Faculty grades
    fc = _client(stub_iam, user_id=1, modules=("lms",),
                 permissions=("lms.course.view", "lms.grade.create", "lms.grade.release", "lms.grade.view"))
    resp = fc.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submissions/{s.id}/grade/", {
        "points": 8, "feedback": "Good work",
    }, format="json")
    assert resp.status_code == 201

    # Faculty releases grade
    resp = fc.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submissions/{s.id}/release-grade/", {})
    assert resp.status_code in (200, 201)

    # Student views released grade
    sc = _client(stub_iam, user_id=100, modules=("lms",),
                 permissions=("lms.course.view", "lms.grade.view"))
    resp = sc.get(f"/api/v1/lms/courses/1/assignments/{a.id}/my-grade/")
    assert resp.status_code == 200
