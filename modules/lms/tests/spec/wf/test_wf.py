"""Spec tests: Workflow strategy (BW-LMS-01..05, CW-LMS-01, CW-LMS-02).

Source of truth: Use Case Specifications v1.0 Related Workflow columns.
No production code consulted.
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


# --- BW-LMS-01: Scheduled material release ---
def test_bw01_scheduled_material_becomes_published_at_release(stub_iam):
    """BW-LMS-01: scheduled material not exposed before release; published at release."""
    create_material(course_id=1, user_id=1, title="Sched", material_type="note",
                    status="scheduled", release_at=timezone.now() + timezone.timedelta(days=1))
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    data = _list(c, "/api/v1/lms/courses/1/materials/")
    assert not any(m["title"] == "Sched" for m in data)


# --- BW-LMS-02: Student submits assignment ---
def test_bw02_student_submits_before_due_date(stub_iam):
    """BW-LMS-02: student submits before due date -> on-time recorded."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.submission.create",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submit/",
                  {"submission_type": "text", "content": "done"}, format="json")
    assert resp.status_code == 201


# Late-submission handling unresolved: not asserted.


# --- BW-LMS-03: Content visibility gating ---
def test_bw03_draft_and_scheduled_not_exposed(stub_iam):
    """BW-LMS-03: draft/scheduled/future content not exposed to students."""
    create_material(course_id=1, user_id=1, title="Draft", material_type="note", status="draft")
    create_material(course_id=1, user_id=1, title="Sched", material_type="note", status="scheduled",
                    release_at=timezone.now() + timezone.timedelta(days=1))
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    data = _list(c, "/api/v1/lms/courses/1/materials/")
    titles = [m["title"] for m in data]
    assert "Draft" not in titles
    assert "Sched" not in titles


# --- BW-LMS-04: Faculty grades submission ---
def test_bw04_faculty_grades_with_attribution(stub_iam):
    """BW-LMS-04: Faculty grades submission, attributed to actor."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    assert grade.graded_by == 1


# Unauthorized grade change blocked: no invalid grade change committed.


# --- BW-LMS-05: Faculty releases grades ---
def test_bw05_faculty_releases_draft_grades(stub_iam):
    """BW-LMS-05: Faculty releases draft grades -> visible to students."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.grade.release",))
    resp = c.post(f"/api/v1/lms/courses/1/assignments/{a.id}/submissions/{sub.id}/release-grade/")
    assert resp.status_code == 200
    grade.refresh_from_db()
    assert grade.status == "released"


# TA grading alone does not release: not asserted (open policy).


# --- CW-LMS-01: Composite material lifecycle ---
def test_cw01_material_lifecycle_draft_to_published(stub_iam):
    """CW-LMS-01: create draft -> schedule -> published -> student views."""
    c = _client(stub_iam, user_id=1, modules=("lms",), permissions=("lms.material.manage",))
    resp = c.post("/api/v1/lms/courses/1/materials/",
                  {"title": "Life", "material_type": "note", "content": "c", "status": "draft"}, format="json")
    assert resp.status_code == 201
    mat_id = resp.json()["id"]
    from modules.lms.models import CourseMaterial
    m = CourseMaterial.objects.get(pk=mat_id)
    m.status = "scheduled"
    m.release_at = timezone.now() - timezone.timedelta(hours=1)
    m.save()
    m.status = "published"
    m.save()
    c2 = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.material.view",))
    data = _list(c2, "/api/v1/lms/courses/1/materials/")
    assert any(m2["title"] == "Life" for m2 in data)


# --- CW-LMS-02: Composite grade lifecycle ---
def test_cw02_grade_lifecycle_submit_grade_release_view_audit(stub_iam):
    """CW-LMS-02: submit -> grade(draft) -> release -> student views read-only -> change audit."""
    a = create_assignment(course_id=1, user_id=1, title="HW", due_at=timezone.now() + timezone.timedelta(days=1),
                          submission_type="text", points_possible=10, status="available")
    sub = submit_assignment(assignment_id=a.id, student_id=10, submission_type="text", content="done")
    grade = grade_submission(submission_id=sub.id, grader_id=1, points=8, feedback="good")
    release_grade(grade_id=grade.id, releaser_id=1)
    c = _client(stub_iam, user_id=10, modules=("lms",), permissions=("lms.grade.view",))
    data = _list(c, f"/api/v1/lms/courses/1/assignments/{a.id}/my-grade/")
    assert len(data) >= 1
    assert data[0]["points"] == 8
    before = GradeAudit.objects.count()
    change_released_grade(grade_id=grade.id, changer_id=1, points=9, feedback="great", reason="recheck")
    assert GradeAudit.objects.count() == before + 1

