from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import ContentStatus, GradeStatus, Role, SubmissionType
from modules.lms.models import (
    Announcement,
    Assignment,
    Course,
    CourseMembership,
    Grade,
    ModuleSection,
    Submission,
)


@pytest.fixture
def auth_client(stub_iam):
    def _client(user_id: int, is_staff: bool = False):
        kind = "staff" if is_staff else "student"
        stub_iam(make_session(user_id=user_id, kind=kind))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token mock-test-token")
        return c

    return _client


@pytest.fixture
def lms_course(db):
    course = Course.objects.create(
        code="CS901",
        title="Cloud Computing & API Testing",
        academic_year=2026,
        semester=1,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=1001,
        role=Role.STUDENT,
        is_active=True,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=2001,
        role=Role.INSTRUCTOR,
        is_active=True,
    )
    return course


@pytest.mark.django_db
def test_courses_api_endpoints(auth_client, lms_course):
    client = auth_client(user_id=1001)

    # List courses
    resp = client.get("/api/v1/lms/courses/")
    assert resp.status_code == 200
    results = resp.json()["results"] if "results" in resp.json() else resp.json()
    assert any(c["id"] == lms_course.id for c in results)

    # Course detail
    detail_resp = client.get(f"/api/v1/lms/courses/{lms_course.id}/")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["code"] == "CS901"


@pytest.mark.django_db
def test_course_nested_actions(auth_client, lms_course):
    sec = ModuleSection.objects.create(course=lms_course, title="API Architecture", order=1)
    ann = Announcement.objects.create(
        course=lms_course,
        author_user_id=2001,
        author_role=Role.INSTRUCTOR,
        title="Welcome to CS901",
        content="First lecture on Monday",
    )
    asg = Assignment.objects.create(
        course=lms_course,
        author_user_id=2001,
        title="REST API Assignment",
        status=ContentStatus.PUBLISHED,
        release_date=timezone.now() - timedelta(days=1),
    )

    client = auth_client(user_id=1001)

    # Sections action
    sec_resp = client.get(f"/api/v1/lms/courses/{lms_course.id}/sections/")
    assert sec_resp.status_code == 200
    assert len(sec_resp.json()) == 1
    assert sec_resp.json()[0]["title"] == "API Architecture"

    # Announcements action
    ann_resp = client.get(f"/api/v1/lms/courses/{lms_course.id}/announcements/")
    assert ann_resp.status_code == 200
    assert len(ann_resp.json()) == 1
    assert ann_resp.json()[0]["title"] == "Welcome to CS901"

    # Assignments action
    asg_resp = client.get(f"/api/v1/lms/courses/{lms_course.id}/assignments/")
    assert asg_resp.status_code == 200
    assert len(asg_resp.json()) == 1
    assert asg_resp.json()[0]["title"] == "REST API Assignment"


@pytest.mark.django_db
def test_assignment_submit_and_submissions(auth_client, lms_course):
    asg = Assignment.objects.create(
        course=lms_course,
        author_user_id=2001,
        title="Project Milestone 1",
        status=ContentStatus.PUBLISHED,
    )

    student_client = auth_client(user_id=1001)

    # Submit assignment
    submit_payload = {
        "submission_type": SubmissionType.TEXT,
        "content_text": "GitHub repo link and summary notes.",
    }
    resp = student_client.post(
        f"/api/v1/lms/assignments/{asg.id}/submit/",
        data=submit_payload,
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["student_user_id"] == 1001
    assert resp.json()["version"] == 1

    # Student retrieves submissions
    subs_resp = student_client.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert subs_resp.status_code == 200
    assert len(subs_resp.json()) == 1


@pytest.mark.django_db
def test_submission_grading_and_audit_logs(auth_client, lms_course):
    asg = Assignment.objects.create(
        course=lms_course,
        author_user_id=2001,
        title="Final Project",
        status=ContentStatus.PUBLISHED,
    )
    sub = Submission.objects.create(
        assignment=asg,
        student_user_id=1001,
        version=1,
        submission_type=SubmissionType.FILE,
    )

    instructor_client = auth_client(user_id=2001, is_staff=True)

    # Draft grade
    draft_payload = {
        "action": "draft",
        "role": Role.INSTRUCTOR,
        "points": 88,
        "feedback": "Minor docstring issue",
    }
    draft_resp = instructor_client.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data=draft_payload,
        format="json",
    )
    assert draft_resp.status_code == 200
    assert draft_resp.json()["status"] == GradeStatus.DRAFT

    # Release grade
    release_payload = {
        "action": "release",
        "role": Role.INSTRUCTOR,
        "points": 92,
        "feedback": "Fixed after review",
        "reason": "Final evaluation complete",
    }
    release_resp = instructor_client.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data=release_payload,
        format="json",
    )
    assert release_resp.status_code == 200
    grade_data = release_resp.json()
    assert grade_data["status"] == GradeStatus.RELEASED
    assert grade_data["points_awarded"] == 92

    # Query audit logs
    logs_resp = instructor_client.get(f"/api/v1/lms/grades/{grade_data['id']}/audit_logs/")
    assert logs_resp.status_code == 200
    assert len(logs_resp.json()) == 1
    assert logs_resp.json()[0]["new_points"] == 92
