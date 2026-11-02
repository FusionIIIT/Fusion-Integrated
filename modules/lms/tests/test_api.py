from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.integrations.registration import (
    CourseAccess,
    RegistrationSourceUnavailable,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseSection,
    CourseWorkspace,
    SubmissionGrade,
)
from modules.lms.services import access

pytestmark = pytest.mark.django_db

STUDENT_PERMISSIONS = (
    "lms.course.view", "lms.material.view", "lms.announcement.view",
    "lms.assignment.view", "lms.submission.create", "lms.submission.view_self",
    "lms.grade.view_self",
)
FACULTY_PERMISSIONS = (
    "lms.course.view", "lms.course.manage", "lms.material.view",
    "lms.material.manage", "lms.announcement.view", "lms.announcement.create",
    "lms.assignment.view", "lms.assignment.manage", "lms.assignment.publish",
    "lms.submission.view", "lms.grade.manage", "lms.grade.release",
)
TA_PERMISSIONS = (
    "lms.course.view", "lms.material.view", "lms.announcement.view",
    "lms.announcement.create", "lms.submission.view", "lms.grade.manage",
)


@pytest.fixture
def course_access(monkeypatch):
    state = {
        "role": "student", "may_announce": False, "may_grade": False,
        "course": CourseWorkspace.objects.create(
            source_course_id="CS-101", course_code="CS101", title="Foundations"),
    }

    def ref_for(_user_id, course_id):
        if course_id != "CS-101":
            return None
        return CourseAccess(
            course_id="CS-101", code="CS101", title="Foundations",
            role=state["role"], may_announce=state["may_announce"],
            may_grade=state["may_grade"],
        )

    monkeypatch.setattr(access, "source_course_for", ref_for)
    monkeypatch.setattr(access, "source_courses_for",
                        lambda user_id: [ref_for(user_id, "CS-101")])
    return state


def _client(stub_iam, *, user_id, permissions, role="student"):
    stub_iam(make_session(
        user_id=user_id, modules=("lms",), permissions=permissions,
        roles=(role,), active_role=role,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-session")
    return client


def _assignment(course, **overrides):
    now = timezone.now()
    values = {
        "course": course,
        "title": "Quiz 1",
        "due_at": now + timedelta(hours=2),
        "instructions": "Complete the questions.",
        "submission_type": "text",
        "points_possible": 10,
        "status": "available",
        "created_by_user_id": 2,
        "published_at": now,
    }
    values.update(overrides)
    return Assignment.objects.create(**values)


def test_schedule_release_makes_assignment_visible_to_student(
        stub_iam, course_access):
    client = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    release_at = timezone.now() + timedelta(minutes=1)
    assignment = _assignment(course_access["course"], status="scheduled",
                              release_at=release_at)

    before = client.get("/api/v1/lms/courses/CS-101/assignments")
    assert before.status_code == 200
    assert before.json()["results"] == []

    from modules.lms.tasks import release_scheduled_content_now
    result = release_scheduled_content_now(now=release_at)

    assert result["assignments"] == 1
    assignment.refresh_from_db()
    assert assignment.status == "available"
    with freeze_time(release_at):
        after = client.get("/api/v1/lms/courses/CS-101/assignments")
    assert [row["id"] for row in after.json()["results"]] == [assignment.pk]


def test_assignment_download_is_limited_to_visible_assignments(
        stub_iam, course_access, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    course_access["role"] = "faculty"
    faculty = _client(stub_iam, user_id=6001, permissions=FACULTY_PERMISSIONS,
                      role="faculty")
    created = faculty.post("/api/v1/lms/courses/CS-101/assignments", {
        "title": "Quiz with file",
        "due_at": (timezone.now() + timedelta(hours=2)).isoformat(),
        "instructions": "Read the attached brief.",
        "submission_type": "text",
        "points_possible": "10",
        "file": SimpleUploadedFile("brief.pdf", b"course brief"),
    }, format="multipart")
    assert created.status_code == 201
    assignment = Assignment.objects.get(pk=created.json()["id"])
    assert created.json()["download_url"].endswith(
        f"/assignments/{assignment.pk}/download")

    course_access["role"] = "student"
    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    hidden = student.get(
        f"/api/v1/lms/courses/CS-101/assignments/{assignment.pk}/download")
    assert hidden.status_code == 404

    course_access["role"] = "faculty"
    faculty = _client(stub_iam, user_id=6001, permissions=FACULTY_PERMISSIONS,
                      role="faculty")
    published = faculty.post(
        f"/api/v1/lms/courses/CS-101/assignments/{assignment.pk}/publish")
    assert published.status_code == 200
    course_access["role"] = "student"
    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    response = student.get(
        f"/api/v1/lms/courses/CS-101/assignments/{assignment.pk}/download")
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"course brief"

def test_submission_records_ownership_and_status_and_blocks_repeat(
        stub_iam, course_access):
    assignment = _assignment(course_access["course"])
    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    path = f"/api/v1/lms/courses/CS-101/assignments/{assignment.pk}/submit"

    created = student.post(path, {"content_type": "text", "text": "My answer"},
                           format="json")
    assert created.status_code == 201
    row = AssignmentSubmission.objects.get(pk=created.json()["id"])
    assert row.user_id == 1001
    assert created.json()["status"] == "submitted"

    repeated = student.post(path, {"content_type": "text", "text": "Again"},
                            format="json")
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "resubmission_policy_unresolved"

    other = _client(stub_iam, user_id=2002, permissions=STUDENT_PERMISSIONS)
    own_history = other.get("/api/v1/lms/courses/CS-101/submissions")
    assert own_history.status_code == 200
    assert own_history.json()["results"] == []


def test_submission_type_and_late_policy_are_enforced_without_inventing_policy(
        stub_iam, course_access):
    assignment = _assignment(course_access["course"])
    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    path = f"/api/v1/lms/courses/CS-101/assignments/{assignment.pk}/submit"

    mismatch = student.post(path, {"content_type": "link", "link": "https://example.com"},
                            format="json")
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "submission_type_mismatch"

    assignment.due_at = timezone.now() - timedelta(seconds=1)
    assignment.save(update_fields=["due_at"])
    late = student.post(path, {"content_type": "text", "text": "Late answer"},
                        format="json")
    assert late.status_code == 409
    assert late.json()["error"]["code"] == "late_submission_policy_unresolved"
    assert not AssignmentSubmission.objects.filter(assignment=assignment).exists()


def test_observer_cannot_read_submissions_or_write_course_content(
        stub_iam, course_access):
    course_access["role"] = "observer"
    observer = _client(stub_iam, user_id=3001,
                       permissions=("lms.course.view", "lms.material.view",
                                    "lms.announcement.view"), role="observer")
    assignment = _assignment(course_access["course"])

    assert observer.get("/api/v1/lms/courses/CS-101/submissions").status_code == 404
    assert observer.get("/api/v1/lms/courses/CS-101/grades").status_code == 404
    assert observer.post("/api/v1/lms/courses/CS-101/sections", {
        "kind": "week", "title": "Week 1",
    }, format="json").status_code == 403
    assert observer.post(
        f"/api/v1/lms/courses/CS-101/assignments/{assignment.pk}/submit", {
            "content_type": "text", "text": "No",
        }, format="json").status_code == 403


def test_ta_capabilities_and_faculty_grade_release(
        stub_iam, course_access):
    assignment = _assignment(course_access["course"])
    submission = AssignmentSubmission.objects.create(
        assignment=assignment, user_id=1001, content_type="text",
        text="answer", submitted_at=timezone.now(),
    )
    ta = _client(stub_iam, user_id=5001, permissions=TA_PERMISSIONS,
                 role="teaching_assistant")
    course_access["role"] = "teaching_assistant"

    denied = ta.post(
        f"/api/v1/lms/courses/CS-101/submissions/{submission.pk}/grade",
        {"points": "8", "feedback": "Good"}, format="json")
    assert denied.status_code == 403
    assert not SubmissionGrade.objects.filter(submission=submission).exists()

    course_access["may_grade"] = True
    graded = ta.post(
        f"/api/v1/lms/courses/CS-101/submissions/{submission.pk}/grade",
        {"points": "8", "feedback": "Good"}, format="json")
    assert graded.status_code == 200
    assert graded.json()["status"] == "draft"
    grade = SubmissionGrade.objects.get(submission=submission)
    assert grade.graded_by_user_id == 5001

    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    course_access["role"] = "student"
    assert student.get("/api/v1/lms/courses/CS-101/grades").json()["results"] == []

    faculty = _client(stub_iam, user_id=6001, permissions=FACULTY_PERMISSIONS,
                      role="faculty")
    course_access["role"] = "faculty"
    released = faculty.post("/api/v1/lms/courses/CS-101/grades",
                            {"grade_ids": [grade.pk]}, format="json")
    assert released.status_code == 200
    grade.refresh_from_db()
    assert grade.status == "released"
    assert grade.released_by_user_id == 6001

    course_access["role"] = "student"
    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    visible = student.get("/api/v1/lms/courses/CS-101/grades")
    assert [row["id"] for row in visible.json()["results"]] == [grade.pk]


def test_material_visibility_announcement_capability_and_course_scope(
        stub_iam, course_access):
    faculty = _client(stub_iam, user_id=6001, permissions=FACULTY_PERMISSIONS,
                      role="faculty")
    course_access["role"] = "faculty"
    course = course_access["course"]
    section = CourseSection.objects.create(course=course, kind="week", title="Week 1")
    unpublished = CourseMaterial.objects.create(
        course=course, section=section, kind="note", title="Hidden", note="hidden",
        status="scheduled", release_at=timezone.now() + timedelta(days=1),
        created_by_user_id=6001,
    )
    published = CourseMaterial.objects.create(
        course=course, section=section, kind="note", title="Visible", note="visible",
        status="published", created_by_user_id=6001,
        published_at=timezone.now(),
    )
    announce = faculty.post("/api/v1/lms/courses/CS-101/announcements", {
        "title": "Welcome", "content": "Welcome to class",
    }, format="json")
    assert announce.status_code == 201
    assert CourseAnnouncement.objects.filter(course=course).count() == 1

    course_access["role"] = "student"
    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)
    materials = student.get("/api/v1/lms/courses/CS-101/materials").json()["results"]
    assert [row["id"] for row in materials] == [published.pk]
    assert unpublished.pk not in [row["id"] for row in materials]

    from modules.lms.tasks import release_scheduled_content_now
    result = release_scheduled_content_now(now=unpublished.release_at)
    assert result["materials"] == 1
    with freeze_time(unpublished.release_at):
        released = student.get("/api/v1/lms/courses/CS-101/materials").json()["results"]
    assert {row["id"] for row in released} == {published.pk, unpublished.pk}

    course_access["role"] = "teaching_assistant"
    ta = _client(stub_iam, user_id=5001, permissions=TA_PERMISSIONS,
                 role="teaching_assistant")
    denied = ta.post("/api/v1/lms/courses/CS-101/announcements", {
        "title": "Unauthorized", "content": "Not permitted",
    }, format="json")
    assert denied.status_code == 403
    course_access["may_announce"] = True
    allowed = ta.post("/api/v1/lms/courses/CS-101/announcements", {
        "title": "TA update", "content": "A permitted update",
    }, format="json")
    assert allowed.status_code == 201

    assert student.get("/api/v1/lms/courses/OTHER-COURSE").status_code == 404


def test_course_access_source_outage_returns_unavailable_without_exposing_course(
        stub_iam, course_access, monkeypatch):
    def unavailable(*_args):
        raise RegistrationSourceUnavailable("provider offline")

    monkeypatch.setattr(access, "source_course_for", unavailable)
    student = _client(stub_iam, user_id=1001, permissions=STUDENT_PERMISSIONS)

    response = student.get("/api/v1/lms/courses/CS-101")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "course_registration_unavailable"
