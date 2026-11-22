"""Tests for LMS REST API endpoints."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
)
from modules.lms.registry import _FACULTY, _STUDENT, _TA

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_world():
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=801,
        course_code="CS601",
        title="Computer Networks",
        syllabus="Routing, TCP/IP, Congestion Control",
        schedule_info="MWF 11-12",
    )
    CourseMembership.objects.create(
        course_id=801,
        user_id=8001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=801,
        user_id=8002,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=True,
        can_grade=True,
    )
    CourseMembership.objects.create(
        course_id=801,
        user_id=8003,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )

    mat = CourseMaterial.objects.create(
        course_id=801,
        title="TCP RFC",
        material_type=MaterialType.LINK,
        external_url="https://tools.ietf.org/rfc/rfc793.txt",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=8001,
    )

    ann = CourseAnnouncement.objects.create(
        course_id=801,
        title="Lab 1 Posted",
        content="Check the assignments tab.",
        author_id=8001,
        author_role=CourseRole.INSTRUCTOR,
    )

    ass = Assignment.objects.create(
        course_id=801,
        title="Socket Programming Lab",
        instructions="Implement a client-server socket in Python.",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=8001,
    )

    sub = AssignmentSubmission.objects.create(
        assignment=ass,
        student_id=8003,
        submission_type=SubmissionType.TEXT,
        content_text="import socket\ns = socket.socket()",
    )

    return {
        "workspace": ws,
        "material": mat,
        "announcement": ann,
        "assignment": ass,
        "submission": sub,
    }


def _client_for(stub_iam, uid, perms, kind="student", role="student"):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            active_role=role,
            roles=(role,),
            modules=("lms",),
            permissions=perms,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-123")
    return client


def test_courses_api(stub_iam, api_world):
    # Student view
    c = _client_for(stub_iam, uid=8003, perms=_STUDENT, kind="student", role="student")
    r = c.get("/api/v1/lms/courses/")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["course_code"] == "CS601"

    r = c.get("/api/v1/lms/courses/801/")
    assert r.status_code == 200
    assert r.json()["title"] == "Computer Networks"

    # Instructor update
    c = _client_for(stub_iam, uid=8001, perms=_FACULTY, kind="faculty", role="faculty")
    r = c.patch(
        "/api/v1/lms/courses/801/",
        {"syllabus": "Updated Syllabus: BGP and SDN"},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["syllabus"] == "Updated Syllabus: BGP and SDN"


def test_materials_api(stub_iam, api_world):
    mat = api_world["material"]

    # Student list materials
    c = _client_for(stub_iam, uid=8003, perms=_STUDENT, kind="student", role="student")
    r = c.get("/api/v1/lms/materials/?course_id=801")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Student get detail
    r = c.get(f"/api/v1/lms/materials/{mat.id}/")
    assert r.status_code == 200
    assert r.json()["title"] == "TCP RFC"

    # Instructor create material
    c = _client_for(stub_iam, uid=8001, perms=_FACULTY, kind="faculty", role="faculty")
    r = c.post(
        "/api/v1/lms/materials/",
        {
            "course_id": 801,
            "title": "BGP Notes",
            "material_type": "NOTE",
            "content_text": "Read BGP convergence notes.",
            "section_name": "Routing",
            "sort_order": 2,
        },
        format="json",
    )
    assert r.status_code == 201
    new_mat_id = r.json()["id"]

    # Instructor update material
    r = c.patch(
        f"/api/v1/lms/materials/{new_mat_id}/",
        {"title": "BGP Deep Dive"},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["title"] == "BGP Deep Dive"

    # Instructor delete material
    r = c.delete(f"/api/v1/lms/materials/{new_mat_id}/")
    assert r.status_code == 204


def test_announcements_api(stub_iam, api_world):
    # Student list announcements
    c = _client_for(stub_iam, uid=8003, perms=_STUDENT, kind="student", role="student")
    r = c.get("/api/v1/lms/announcements/?course_id=801")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # TA posts announcement
    c = _client_for(stub_iam, uid=8002, perms=_TA, kind="student", role="teaching_assistant")
    r = c.post(
        "/api/v1/lms/announcements/",
        {
            "course_id": 801,
            "title": "TA Tutorial Session",
            "content": "Join us tomorrow at 5 PM on Zoom.",
        },
        format="json",
    )
    assert r.status_code == 201
    ann_id = r.json()["id"]

    # Instructor patches announcement
    c = _client_for(stub_iam, uid=8001, perms=_FACULTY, kind="faculty", role="faculty")
    r = c.patch(
        f"/api/v1/lms/announcements/{ann_id}/",
        {"title": "TA Tutorial Session (Rescheduled)"},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["title"] == "TA Tutorial Session (Rescheduled)"

    # Instructor deletes announcement
    r = c.delete(f"/api/v1/lms/announcements/{ann_id}/")
    assert r.status_code == 204


def test_assignments_and_submissions_api(stub_iam, api_world):
    ass = api_world["assignment"]

    # Student list assignments
    c = _client_for(stub_iam, uid=8003, perms=_STUDENT, kind="student", role="student")
    r = c.get("/api/v1/lms/assignments/?course_id=801")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Student submit
    r = c.post(
        f"/api/v1/lms/assignments/{ass.id}/submissions/",
        {
            "submission_type": "TEXT",
            "content_text": "Updated client server solution",
        },
        format="json",
    )
    assert r.status_code == 201
    sub_id = r.json()["id"]

    # Student retrieve own submission detail
    r = c.get(f"/api/v1/lms/submissions/{sub_id}/")
    assert r.status_code == 200
    assert r.json()["student_id"] == 8003

    # Instructor create new assignment in DRAFT
    c = _client_for(stub_iam, uid=8001, perms=_FACULTY, kind="faculty", role="faculty")
    now = timezone.now()
    r = c.post(
        "/api/v1/lms/assignments/",
        {
            "course_id": 801,
            "title": "Lab 2: Routing Protocols",
            "instructions": "Implement Dijkstra's algorithm.",
            "points_possible": "100.00",
            "submission_type": "TEXT",
            "due_date": (now + timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    assert r.status_code == 201
    lab2_id = r.json()["id"]
    assert r.json()["status"] == AssignmentStatus.DRAFT

    # Instructor publish assignment
    r = c.post(f"/api/v1/lms/assignments/{lab2_id}/publish/", {}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == AssignmentStatus.PUBLISHED


def test_grading_and_audits_api(stub_iam, api_world):
    sub = api_world["submission"]
    ass = api_world["assignment"]

    # 1. TA grades submission (DRAFT)
    c = _client_for(stub_iam, uid=8002, perms=_TA, kind="student", role="teaching_assistant")
    r = c.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        {
            "points_awarded": 85.0,
            "feedback_text": "Initial feedback from TA",
        },
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["status"] == GradeStatus.DRAFT

    # 2. Student cannot view draft grade yet
    c = _client_for(stub_iam, uid=8003, perms=_STUDENT, kind="student", role="student")
    r = c.get(f"/api/v1/lms/submissions/{sub.id}/grade/")
    assert r.status_code == 404

    # 3. Faculty publishes grades
    c = _client_for(stub_iam, uid=8001, perms=_FACULTY, kind="faculty", role="faculty")
    r = c.post(
        f"/api/v1/lms/assignments/{ass.id}/publish-grades/",
        {"submission_ids": [sub.id]},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["published_count"] == 1

    # 4. Student can now view published grade
    c = _client_for(stub_iam, uid=8003, perms=_STUDENT, kind="student", role="student")
    r = c.get(f"/api/v1/lms/submissions/{sub.id}/grade/")
    assert r.status_code == 200
    assert r.json()["status"] == GradeStatus.PUBLISHED
    assert float(r.json()["points_awarded"]) == 85.0

    # 5. Instructor modifies published grade -> creates audit
    c = _client_for(stub_iam, uid=8001, perms=_FACULTY, kind="faculty", role="faculty")
    r = c.patch(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        {
            "points_awarded": 95.0,
            "feedback_text": "Corrected evaluation",
            "reason": "Grace marks added",
        },
        format="json",
    )
    assert r.status_code == 200
    assert float(r.json()["points_awarded"]) == 95.0

    # 6. Retrieve audit history
    r = c.get(f"/api/v1/lms/submissions/{sub.id}/grade-audit/")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert float(r.json()[0]["old_points"]) == 85.0
    assert float(r.json()[0]["new_points"]) == 95.0
    assert r.json()[0]["reason"] == "Grace marks added"
