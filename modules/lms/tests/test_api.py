"""Tests for LMS REST API endpoints (modules/lms/api/)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.entities import CourseRole
from modules.lms.services import courses as service

pytestmark = pytest.mark.django_db


def _make_client(stub_iam, user_id, permissions):
    stub_iam(
        make_session(
            user_id=user_id,
            modules=("lms",),
            permissions=permissions,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token token-{user_id}")
    return c


@pytest.fixture
def seeded_course():
    c = service.create_course_workspace(
        course_code="CS301",
        title="Database Systems",
        instructor_user_id=10,
        syllabus="Initial syllabus",
    )
    service.enroll_member(
        course_id=c.id,
        user_id=10,
        role=CourseRole.FACULTY.value,
        can_post_announcements=True,
    )
    service.enroll_member(
        course_id=c.id,
        user_id=100,
        role=CourseRole.STUDENT.value,
    )
    return c


def test_course_list_and_detail(stub_iam, seeded_course):
    client_fac = _make_client(stub_iam, 10, ["lms.course.view", "lms.course.manage"])
    resp = client_fac.get("/api/v1/lms/courses/")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["course"] == seeded_course.id
    assert resp.data[0]["role"] == "faculty"

    # Detail view
    resp_detail = client_fac.get(f"/api/v1/lms/courses/{seeded_course.id}/")
    assert resp_detail.status_code == 200
    assert resp_detail.data["title"] == "Database Systems"


def test_materials_and_announcements_api(stub_iam, seeded_course):
    client_fac = _make_client(
        stub_iam,
        10,
        ["lms.course.view", "lms.material.view", "lms.material.upload", "lms.announcement.post"],
    )

    # Upload material
    resp_mat = client_fac.post(
        f"/api/v1/lms/courses/{seeded_course.id}/materials/",
        {
            "title": "Lecture 1 Slides",
            "material_type": "file",
            "section_or_week": "Week 1",
            "file_url": "https://example.com/lec1.pdf",
        },
        format="json",
    )
    assert resp_mat.status_code == 201
    assert resp_mat.data["title"] == "Lecture 1 Slides"

    # Post announcement
    resp_ann = client_fac.post(
        f"/api/v1/lms/courses/{seeded_course.id}/announcements/",
        {
            "title": "Welcome Announcement",
            "content": "Class starts Monday at 9 AM.",
        },
        format="json",
    )
    assert resp_ann.status_code == 201
    assert resp_ann.data["title"] == "Welcome Announcement"

    # Student reads announcements
    client_stu = _make_client(
        stub_iam, 100, ["lms.course.view", "lms.material.view", "lms.assignment.view"]
    )
    resp_ann_stu = client_stu.get(f"/api/v1/lms/courses/{seeded_course.id}/announcements/")
    assert resp_ann_stu.status_code == 200
    assert len(resp_ann_stu.data) == 1


def test_assignment_and_grading_flow_api(stub_iam, seeded_course):
    now = timezone.now()
    client_fac = _make_client(
        stub_iam,
        10,
        [
            "lms.course.view",
            "lms.assignment.view",
            "lms.assignment.create",
            "lms.grade.view",
            "lms.grade.evaluate",
            "lms.grade.release",
            "lms.grade.audit",
        ],
    )

    # Create assignment
    due_str = (now + timedelta(days=7)).isoformat()
    resp_assign = client_fac.post(
        f"/api/v1/lms/courses/{seeded_course.id}/assignments/",
        {
            "title": "Project 1",
            "instructions": "SQL Schema Design",
            "submission_type": "text",
            "points_possible": "100.00",
            "due_date": due_str,
        },
        format="json",
    )
    assert resp_assign.status_code == 201
    assign_id = resp_assign.data["id"]

    # Publish assignment
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{assign_id}/publish/")
    assert resp_pub.status_code == 200
    assert resp_pub.data["status"] == "available"

    # Student submits
    client_stu = _make_client(
        stub_iam,
        100,
        ["lms.course.view", "lms.assignment.view", "lms.assignment.submit", "lms.grade.view"],
    )
    resp_sub = client_stu.post(
        f"/api/v1/lms/assignments/{assign_id}/submissions/",
        {
            "submission_type": "text",
            "submission_content": "CREATE TABLE users (...);",
        },
        format="json",
    )
    assert resp_sub.status_code == 201
    sub_id = resp_sub.data["id"]

    # Faculty grades submission
    client_fac = _make_client(
        stub_iam,
        10,
        [
            "lms.course.view",
            "lms.assignment.view",
            "lms.assignment.create",
            "lms.grade.view",
            "lms.grade.evaluate",
            "lms.grade.release",
            "lms.grade.audit",
        ],
    )
    resp_grade = client_fac.post(
        f"/api/v1/lms/submissions/{sub_id}/grade/",
        {
            "points": "92.50",
            "feedback": "Well-normalized schema.",
        },
        format="json",
    )
    assert resp_grade.status_code == 200
    grade_id = resp_grade.data["id"]
    assert resp_grade.data["status"] == "draft"

    # Release grades
    resp_rel = client_fac.post(f"/api/v1/lms/assignments/{assign_id}/release-grades/")
    assert resp_rel.status_code == 200

    # Modify released grade
    resp_mod = client_fac.patch(
        f"/api/v1/lms/grades/{grade_id}/modify/",
        {
            "new_points": "95.00",
            "reason": "Recounted index question",
        },
        format="json",
    )
    assert resp_mod.status_code == 200
    assert Decimal(str(resp_mod.data["points"])) == Decimal("95.00")

    # Grade audit log
    resp_audit = client_fac.get(f"/api/v1/lms/grades/{grade_id}/audit/")
    assert resp_audit.status_code == 200
    assert len(resp_audit.data) == 1
    assert resp_audit.data[0]["reason"] == "Recounted index question"
