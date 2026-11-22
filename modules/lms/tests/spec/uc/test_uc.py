"""Spec tests: Use Case strategy (UC-LMS-001..015).

Source of truth: Problem Statement v1.0 + Use Case Specifications v1.0.
No production code consulted for test design. Open policy not asserted.
"""
import pytest
from rest_framework.test import APIClient
from django.utils import timezone

from conftest import make_session
from modules.lms.models import (
    Assignment, CourseMaterial, Announcement, Submission, Grade, GradeAudit,
)
from modules.lms.services import (
    create_material, create_announcement, create_assignment, publish_assignment,
    submit_assignment, grade_submission, release_grade, change_released_grade,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _list(c, url):
    data = c.get(url).json()
    return data.get("results", data) if isinstance(data, dict) else data


# --- UC-LMS-001: Access Course Workspace ---
def test_uc001_linked_student_accesses_workspace(stub_iam):
    """UC-LMS-001 MSS: linked student opens course workspace, sees details."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.course.view",))
    resp = c.get("/api/v1/lms/courses/1/")
    assert resp.status_code == 200
    assert resp.json()["course_id"] == 1


def test_uc001_unauthorized_access_denied(stub_iam):
    """UC-LMS-001 AF: access not authorized -> denied (404, never 403)."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.course.view",))
    assert c.get("/api/v1/lms/courses/999/").status_code == 404


# --- UC-LMS-002: Manage Course Details ---
def test_uc002_faculty_manages_course_details(stub_iam):
    """UC-LMS-002 MSS: Faculty edits/publishes course details (200)."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.course.manage",))
    resp = c.patch("/api/v1/lms/courses/1/", {"title": "New Title"}, format="json")
    assert resp.status_code == 200


def test_uc002_unauthorized_faculty_course_rejected(stub_iam):
    """UC-LMS-002 EF: unauthorized Faculty-course combination rejected."""
    c = _client(stub_iam, user_id=5, modules=("lms",), permissions=("lms.course.manage",))
    assert c.patch("/api/v1/lms/courses/999/", {"title": "X"}, format="json").status_code == 404


# --- UC-LMS-003: Manage Course Materials ---
def test_uc003_faculty_creates_published_material(stub_iam):
    """UC-LMS-003 MSS: Faculty adds material, immediate publication -> published."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.material.manage",))
    resp = c.post("/api/v1/lms/courses/1/materials/",
                  {"title": "Mat", "material_type": "note", "content": "c", "status": "published"}, format="json")
    assert resp.status_code == 201


def test_uc003_faculty_creates_scheduled_material(stub_iam):
    """UC-LMS-003 MSS: future release -> status Scheduled."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.material.manage",))
    resp = c.post("/api/v1/lms/courses/1/materials/",
                  {"title": "Sched", "material_type": "note", "content": "c", "status": "scheduled",
                   "release_at": (timezone.now() + timezone.timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 201


def test_uc003_student_write_rejected(stub_iam):
    """UC-LMS-003 EF: Student write attempt rejected."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    assert c.post("/api/v1/lms/courses/1/materials/", {"title": "X"}, format="json").status_code == 403


# --- UC-LMS-004: View Published Course Materials ---
def test_uc004_student_views_published_materials(stub_iam):
    """UC-LMS-004 MSS: student lists published materials, opens read-only."""
    create_material(course_id=1, user_id=1, title="Pub", material_type="note", status="published")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    data = _list(c, "/api/v1/lms/courses/1/materials/")
    assert any(m["title"] == "Pub" for m in data)


def test_uc004_unauthorized_access_denied(stub_iam):
    """UC-LMS-004 EF: unauthorized course access denied."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    assert c.get("/api/v1/lms/courses/999/materials/").status_code == 404


# --- UC-LMS-005: Post Course Announcement ---
def test_uc005_faculty_posts_announcement(stub_iam):
    """UC-LMS-005 MSS: Faculty posts announcement, timestamped, course-wide visible."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.announcement.create",))
    resp = c.post("/api/v1/lms/courses/1/announcements/", {"content": "Hello"}, format="json")
    assert resp.status_code == 201


def test_uc005_unauthorized_posting_rejected(stub_iam):
    """UC-LMS-005 EF: unauthorized posting rejected."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.announcement.view",))
    assert c.post("/api/v1/lms/courses/1/announcements/", {"content": "Hello"}, format="json").status_code == 403


# --- UC-LMS-006: View Course Announcements ---
def test_uc006_student_views_announcements(stub_iam):
    """UC-LMS-006 MSS: announcements retrieved with timestamps."""
    create_announcement(course_id=1, user_id=1, content="Hi")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.announcement.view",))
    data = _list(c, "/api/v1/lms/courses/1/announcements/")
    assert len(data) >= 1
    assert "created_at" in data[0]


# --- UC-LMS-007: Create or Edit Assignment ---
def test_uc007_faculty_creates_draft_assignment(stub_iam):
    """UC-LMS-007 MSS: Faculty creates assignment, stored in Draft."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.assignment.manage",))
    resp = c.post("/api/v1/lms/courses/1/assignments/",
                  {"title": "HW", "instructions": "do it", "submission_type": "text", "points_possible": 10,
                   "due_at": (timezone.now() + timezone.timedelta(days=1)).isoformat(), "status": "draft"},
                  format="json")
    assert resp.status_code == 201


def test_uc007_student_authoring_rejected(stub_iam):
    """UC-LMS-007 EF: Student assignment-authoring rejected."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.assignment.view",))
    assert c.post("/api/v1/lms/courses/1/assignments/", {"title": "HW"}, format="json").status_code == 403


# --- UC-LMS-008: Publish Assignment ---
def test_uc008_faculty_publishes_assignment(stub_iam):
    """UC-LMS-008 MSS: Faculty publishes assignment -> available to students."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="draft")
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.assignment.manage",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/publish/", format="json")
    assert resp.status_code == 200


# --- UC-LMS-009: View Assignment ---
def test_uc009_student_views_available_assignment(stub_iam):
    """UC-LMS-009 MSS: student views available/published assignments for course."""
    create_assignment(course_id=1, user_id=1, title="Avail", due_at=timezone.now() + timezone.timedelta(days=1),
                      submission_type="text", points_possible=10, status="available")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.assignment.view",))
    data = _list(c, "/api/v1/lms/courses/1/assignments/")
    assert any(a["title"] == "Avail" for a in data)


def test_uc009_student_does_not_see_draft(stub_iam):
    """UC-LMS-009: draft assignment not visible to student."""
    create_assignment(course_id=1, user_id=1, title="Draft", due_at=timezone.now() + timezone.timedelta(days=1),
                      submission_type="text", points_possible=10, status="draft")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.assignment.view",))
    data = _list(c, "/api/v1/lms/courses/1/assignments/")
    assert not any(a["title"] == "Draft" for a in data)


# --- UC-LMS-010: Submit Assignment ---
def test_uc010_student_submits_on_time(stub_iam):
    """UC-LMS-010 MSS: student submits before due date -> on-time recorded."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.create",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submit/",
                  {"submission_type": "text", "content": "done"}, format="json")
    assert resp.status_code == 201


# Late-submission behavior unresolved (ISS-LMS-001): intentionally not asserted.


# --- UC-LMS-011: View Own Submission History ---
def test_uc011_student_views_own_submissions_only(stub_iam):
    """UC-LMS-011 MSS: student views own submission history/status only."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="s10")
    submit_assignment(assignment_id=a.id, student_id=11, submission_type="text", content="s11")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.view_own",))
    data = _list(c, f"/api/v1/lms/courses/1/assignments/{a.id}/my-submission/")
    ids = [s["user_id"] for s in data]
    assert 10 in ids
    assert 11 not in ids


# --- UC-LMS-012: Grade Submission ---
def test_uc012_faculty_grades_submission_with_attribution(stub_iam):
    """UC-LMS-012 MSS: Faculty grades submission, attributed to actor."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    assert grade.graded_by == 1
    assert grade.points == 8


# --- UC-LMS-013: Release Grades ---
def test_uc013_faculty_releases_grades(stub_iam):
    """UC-LMS-013 MSS: Faculty releases draft grades -> visible to students."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.grade.release",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submissions/{sub.id}/release-grade/")
    assert resp.status_code == 200
    grade.refresh_from_db()
    assert grade.status == "released"


# TA grading alone does not release grades: not asserted (open policy).


# --- UC-LMS-014: View Own Released Grade ---
def test_uc014_student_views_released_grade_readonly(stub_iam):
    """UC-LMS-014 MSS: student views own released grade/feedback read-only."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    release_grade(grade_id=grade.id, releaser_id=1)
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.grade.view",))
    data = _list(c, f"/api/v1/lms/courses/1/assignments/{a.id}/my-grade/")
    assert len(data) >= 1
    assert data[0]["points"] == 8


# --- UC-LMS-015: Scheduled Release ---
def test_uc015_scheduled_release_not_premature(stub_iam):
    """UC-LMS-015 MSS: scheduled content not exposed before release time."""
    create_material(course_id=1, user_id=1, title="Sched", material_type="note",
                    status="scheduled", release_at=timezone.now() + timezone.timedelta(days=1))
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    data = _list(c, "/api/v1/lms/courses/1/materials/")
    assert not any(m["title"] == "Sched" for m in data)



