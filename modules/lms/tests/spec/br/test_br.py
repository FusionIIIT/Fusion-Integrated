"""Spec tests: Business Rules strategy (BR-LMS-001..019).

Source of truth: Problem Statement v1.0 + Business Rule Specifications v1.0.
No production code consulted for test design. Unresolved policy is not asserted.
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


# --- BR-LMS-001: Course-specific access control ---
def test_br001_linked_user_sees_course_workspace(stub_iam):
    """BR-LMS-001: user linked to course 1 gets course 1 workspace (200)."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.course.view",))
    resp = c.get("/api/v1/lms/courses/1/")
    assert resp.status_code == 200
    assert resp.json()["course_id"] == 1


def test_br001_unlinked_user_gets_404_not_403(stub_iam):
    """BR-LMS-001: user NOT linked to course 99 gets 404 (never 403)."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.course.view",))
    resp = c.get("/api/v1/lms/courses/99/")
    assert resp.status_code == 404


# --- BR-LMS-003: Observer read-only and student-data restriction ---
def test_br003_observer_can_view_course(stub_iam):
    """BR-LMS-003: Observer with view perms GETs course/materials/announcements (200)."""
    perms = ("lms.course.view", "lms.material.view", "lms.announcement.view")
    c = _client(stub_iam, user_id=2, modules=("lms",), permissions=perms)
    assert c.get("/api/v1/lms/courses/1/").status_code == 200
    assert c.get("/api/v1/lms/courses/1/materials/").status_code == 200
    assert c.get("/api/v1/lms/courses/1/announcements/").status_code == 200


def test_br003_observer_no_write_access(stub_iam):
    """BR-LMS-003: Observer has no write permission -> POST rejected (403)."""
    c = _client(stub_iam, user_id=2, modules=("lms",), permissions=("lms.material.view",))
    resp = c.post("/api/v1/lms/courses/1/materials/", {"title": "X"}, format="json")
    assert resp.status_code == 403


# --- BR-LMS-004: TA authoring restriction ---
def test_br004_ta_cannot_create_material_or_assignment(stub_iam):
    """BR-LMS-004: TA (no manage perms) POST material/assignment -> 403."""
    c = _client(stub_iam, user_id=3, modules=("lms",),
                permissions=("lms.course.view", "lms.material.view",
                             "lms.announcement.view", "lms.assignment.view",
                             "lms.grade.create"))
    assert c.post("/api/v1/lms/courses/1/materials/", {"title": "X"}, format="json").status_code == 403
    assert c.post("/api/v1/lms/courses/1/assignments/", {"title": "A"}, format="json").status_code == 403


# --- BR-LMS-005: Published material visibility ---
def test_br005_student_sees_only_published_materials(stub_iam):
    """BR-LMS-005: student lists materials -> only published, draft omitted."""
    create_material(course_id=1, user_id=1, title="Draft", material_type="note", status="draft")
    create_material(course_id=1, user_id=1, title="Pub", material_type="note", status="published")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    resp = c.get("/api/v1/lms/courses/1/materials/")
    data = resp.json()
    data = data.get("results", data) if isinstance(data, dict) else data
    titles = [m["title"] for m in data]
    assert "Pub" in titles
    assert "Draft" not in titles


# --- BR-LMS-006: Scheduled material release ---
def test_br006_scheduled_material_omitted_for_student(stub_iam):
    """BR-LMS-006: scheduled material not exposed to student before release."""
    create_material(course_id=1, user_id=1, title="Sched", material_type="note",
                    status="scheduled", release_at=timezone.now() + timezone.timedelta(days=1))
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    resp = c.get("/api/v1/lms/courses/1/materials/")
    data = resp.json()
    data = data.get("results", data) if isinstance(data, dict) else data
    titles = [m["title"] for m in data]
    assert "Sched" not in titles


# --- BR-LMS-007: Announcement posting authority ---
def test_br007_faculty_can_post_announcement(stub_iam):
    """BR-LMS-007: Faculty with announcement.create POSTs announcement (201)."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.announcement.create",))
    resp = c.post("/api/v1/lms/courses/1/announcements/", {"content": "Hello"}, format="json")
    assert resp.status_code == 201


def test_br007_student_cannot_post_announcement(stub_iam):
    """BR-LMS-007: Student (view only) POST announcement -> 403."""
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.announcement.view",))
    resp = c.post("/api/v1/lms/courses/1/announcements/", {"content": "Hello"}, format="json")
    assert resp.status_code == 403


# --- BR-LMS-008: Announcement timestamp and audience ---
def test_br008_announcement_visible_with_timestamp(stub_iam):
    """BR-LMS-008: announcement created, student and faculty both see it with created_at."""
    create_announcement(course_id=1, user_id=1, content="Hi")
    perms = ("lms.announcement.view",)
    c1 = _client(stub_iam, user_id=10, modules=("lms",), permissions=perms)
    c2 = _client(stub_iam, user_id=1, modules=("lms",), permissions=perms)
    for c in (c1, c2):
        resp = c.get("/api/v1/lms/courses/1/announcements/")
        assert resp.status_code == 200
        data = resp.json()
        data = data.get("results", data) if isinstance(data, dict) else data
        assert len(data) >= 1
        assert "created_at" in data[0]


# --- BR-LMS-009: Assignment required configuration ---
def test_br009_assignment_requires_due_at(stub_iam):
    """BR-LMS-009: POST assignment missing due_at -> 400."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.assignment.manage",))
    resp = c.post("/api/v1/lms/courses/1/assignments/",
                  {"title": "HW", "instructions": "do it", "submission_type": "text", "points_possible": 10},
                  format="json")
    assert resp.status_code == 400


# --- BR-LMS-010: Assignment draft-before-publication ---
def test_br010_draft_assignment_omitted_for_student(stub_iam):
    """BR-LMS-010: draft assignment not visible to student."""
    create_assignment(course_id=1, user_id=1, title="Draft HW", due_at=timezone.now(),
                      submission_type="text", points_possible=10, status="draft")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.assignment.view",))
    resp = c.get("/api/v1/lms/courses/1/assignments/")
    data = resp.json()
    data = data.get("results", data) if isinstance(data, dict) else data
    titles = [a["title"] for a in data]
    assert "Draft HW" not in titles


# --- BR-LMS-011: Assignment release-date visibility ---
def test_br011_future_release_assignment_omitted(stub_iam):
    """BR-LMS-011: available assignment with future release_at not visible to student."""
    create_assignment(course_id=1, user_id=1, title="Future HW", due_at=timezone.now() + timezone.timedelta(days=2),
                      submission_type="text", points_possible=10, status="available",
                      release_at=timezone.now() + timezone.timedelta(days=1))
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.assignment.view",))
    resp = c.get("/api/v1/lms/courses/1/assignments/")
    data = resp.json()
    data = data.get("results", data) if isinstance(data, dict) else data
    titles = [a["title"] for a in data]
    assert "Future HW" not in titles


# --- BR-LMS-012: Submission-type conformity ---
def test_br012_wrong_submission_type_rejected(stub_iam):
    """BR-LMS-012: assignment submission_type=text, student submits file -> 400."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.create",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submit/",
                  {"submission_type": "file", "content": ""}, format="json")
    assert resp.status_code == 400


# --- BR-LMS-013: Baseline on-time submission ---
def test_br013_on_time_submission_recorded(stub_iam):
    """BR-LMS-013: student submits before due_date -> 201, submission recorded."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.create",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submit/",
                  {"submission_type": "text", "content": "done"}, format="json")
    assert resp.status_code == 201


# Late-submission behavior is unresolved (ISS-LMS-001): intentionally not asserted.


# --- BR-LMS-014: Submission ownership/privacy ---
def test_br014_student_sees_only_own_submissions(stub_iam):
    """BR-LMS-014: student 2 lists submissions for assignment -> only student 2's."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="s10")
    submit_assignment(assignment_id=a.id, student_id=11, submission_type="text", content="s11")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.view_own",))
    resp = c.get(f"/api/v1/lms/courses/1/assignments/{a.id}/my-submission/")
    data = resp.json()
    data = data.get("results", data) if isinstance(data, dict) else data
    ids = [s["user_id"] for s in data]
    assert 10 in ids
    assert 11 not in ids


# --- BR-LMS-015: Grading authority and attribution ---
def test_br015_grade_recorded_with_grader_attribution(stub_iam):
    """BR-LMS-015: Faculty grades submission -> grade has graded_by = faculty."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    assert grade.graded_by == 1
    assert grade.points == 8


# --- BR-LMS-016: Draft grade visibility ---
def test_br016_draft_grade_hidden_from_student(stub_iam):
    """BR-LMS-016: draft grade not returned to student."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")  # stays draft
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.grade.view",))
    resp = c.get(f"/api/v1/lms/courses/1/assignments/{a.id}/my-grade/")
    assert resp.status_code == 200
    assert resp.json() == [] or resp.json() is None


# --- BR-LMS-017: Grade release authority ---
def test_br017_faculty_can_release_grade(stub_iam):
    """BR-LMS-017: Faculty with grade.release releases draft grade."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.grade.release",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submissions/{sub.id}/release-grade/")
    assert resp.status_code == 200
    grade.refresh_from_db()
    assert grade.status == "released"


# --- BR-LMS-018: Released grade read-only to Student ---
def test_br018_student_sees_released_grade_readonly(stub_iam):
    """BR-LMS-018: released grade visible to student in read-only form."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    release_grade(grade_id=grade.id, releaser_id=1)
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.grade.view",))
    resp = c.get(f"/api/v1/lms/courses/1/assignments/{a.id}/my-grade/")
    assert resp.status_code == 200
    data = resp.json()
    data = data.get("results", data) if isinstance(data, dict) else data
    assert len(data) >= 1
    assert data[0]["points"] == 8
    assert data[0]["feedback"] == "good"


# --- BR-LMS-019: Post-release grade-change audit ---
def test_br019_grade_change_creates_audit_record(stub_iam):
    """BR-LMS-019: released grade changed -> GradeAudit records who and when."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    release_grade(grade_id=grade.id, releaser_id=1)
    before = GradeAudit.objects.count()
    change_released_grade(grade_id=grade.id, changer_id=1, points=9, feedback="great", reason="recheck")
    assert GradeAudit.objects.count() == before + 1
    audit = GradeAudit.objects.latest("id")
    assert audit.changed_by == 1
    assert audit.old_points == 8
    assert audit.new_points == 9



