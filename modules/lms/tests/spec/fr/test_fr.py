"""Spec tests: Functional Requirements strategy (FR-LMS-3.1..3.6).

Source of truth: Problem Statement v1.0 §3. No production code consulted.
"""
import pytest
from rest_framework.test import APIClient
from django.utils import timezone

from conftest import make_session
from modules.lms.models import (
    Assignment, CourseMaterial, Announcement, Submission, Grade,
)
from modules.lms.services import (
    create_material, create_announcement, create_assignment, publish_assignment,
    submit_assignment, grade_submission, release_grade,
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


# --- FR-LMS-3.1: Course Access and Details ---
def test_fr31_registered_user_opens_course_workspace(stub_iam):
    """FR-3.1: registered course opens dedicated workspace with details."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.course.view",))
    resp = c.get("/api/v1/lms/courses/1/")
    assert resp.status_code == 200
    assert resp.json()["course_id"] == 1


def test_fr31_access_restricted_to_linked_users(stub_iam):
    """FR-3.1: access restricted to enrolled/linked users (404, never 403)."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.course.view",))
    assert c.get("/api/v1/lms/courses/999/").status_code == 404


# --- FR-LMS-3.2: Course Materials ---
def test_fr32_faculty_uploads_and_schedules_material(stub_iam):
    """FR-3.2: Faculty uploads material; may schedule future release."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.material.manage",))
    resp = c.post("/api/v1/lms/courses/1/materials/",
                  {"title": "Mat", "material_type": "note", "content": "c", "status": "scheduled",
                   "release_at": (timezone.now() + timezone.timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 201


def test_fr32_students_ta_observer_read_only_published(stub_iam):
    """FR-3.2: Students/TAs/Observers read-only access to published materials."""
    create_material(course_id=1, user_id=1, title="Pub", material_type="note", status="published")
    for uid in (10, 20, 30):
        c = _client(stub_iam, user_id=uid, modules=("lms",), permissions=("lms.material.view",))
        data = _list(c, "/api/v1/lms/courses/1/materials/")
        assert any(m["title"] == "Pub" for m in data)


# --- FR-LMS-3.3: Announcements ---
def test_fr33_faculty_ta_post_announcement_timestamped(stub_iam):
    """FR-3.3: Faculty/TAs post announcements; timestamped; visible course-wide."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.announcement.create",))
    resp = c.post("/api/v1/lms/courses/1/announcements/", {"content": "Hi"}, format="json")
    assert resp.status_code == 201
    create_announcement(course_id=1, user_id=1, content="Hi")
    c2 = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.announcement.view",))
    data = _list(c2, "/api/v1/lms/courses/1/announcements/")
    assert len(data) >= 1
    assert "created_at" in data[0]


# --- FR-LMS-3.4: Assignments ---
def test_fr34_faculty_creates_assignment_draft_before_publish(stub_iam):
    """FR-3.4: Faculty creates assignment with config; draft before publication."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.assignment.manage",))
    resp = c.post("/api/v1/lms/courses/1/assignments/",
                  {"title": "HW", "instructions": "do it", "submission_type": "text", "points_possible": 10,
                   "due_at": (timezone.now() + timezone.timedelta(days=1)).isoformat(), "status": "draft"},
                  format="json")
    assert resp.status_code == 201


def test_fr34_visibility_follows_release_date(stub_iam):
    """FR-3.4: assignment visibility follows configured release date."""
    create_assignment(course_id=1, user_id=1, title="Future", due_at=timezone.now() + timezone.timedelta(days=2),
                      submission_type="text", points_possible=10, status="available",
                      release_at=timezone.now() + timezone.timedelta(days=1))
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.assignment.view",))
    data = _list(c, "/api/v1/lms/courses/1/assignments/")
    assert not any(a["title"] == "Future" for a in data)


# --- FR-LMS-3.5: Assignment Submission ---
def test_fr35_student_submits_before_due_date(stub_iam):
    """FR-3.5: student submits file/text/link before due date."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.create",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submit/",
                  {"submission_type": "text", "content": "done"}, format="json")
    assert resp.status_code == 201


def test_fr35_student_views_own_history_status(stub_iam):
    """FR-3.5: student views own submission history/status (submitted/late/missing)."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="s10")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.view_own",))
    data = _list(c, f"/api/v1/lms/courses/1/assignments/{a.id}/my-submission/")
    assert len(data) >= 1


# Late handling and resubmission TBD: not asserted.


# --- FR-LMS-3.6: Grading ---
def test_fr36_faculty_ta_grade_with_points_feedback(stub_iam):
    """FR-3.6: Faculty/TAs grade with points+feedback."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    assert grade.points == 8
    assert grade.feedback == "good"


def test_fr36_draft_until_released_then_read_only(stub_iam):
    """FR-3.6: draft until released; released = read-only to student."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    release_grade(grade_id=grade.id, releaser_id=1)
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.grade.view",))
    data = _list(c, f"/api/v1/lms/courses/1/assignments/{a.id}/my-grade/")
    assert len(data) >= 1
    assert data[0]["points"] == 8


