"""Specification business rule tests for LMS Course Announcements.

Covers:
- TC-BR-014 / BR-LMS-007 permitted (Faculty): Faculty permitted to post announcements
- TC-BR-015 / BR-LMS-007 permitted (TA with permission): TA with permission permitted to post
- TC-BR-016 / BR-LMS-007 prohibited (TA without permission): TA without permission prohibited
- TC-BR-017 / BR-LMS-008 permitted: Posted announcement timestamped and visible course-wide
- TC-BR-018 / BR-LMS-008 prohibited: Unassociated users prohibited from announcements
"""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import CourseRole, MembershipStatus
from modules.lms.models import CourseAnnouncement, CourseMembership, CourseWorkspace
from modules.lms.registry import _FACULTY, _OBSERVER, _STUDENT, _TA

pytestmark = pytest.mark.django_db


def _make_client(
    stub_iam,
    user_id: int,
    perms: list[str],
    kind: str = "student",
    role: str = "student",
) -> APIClient:
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            active_role=role,
            roles=(role,),
            modules=("lms",),
            permissions=perms,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token tok-{user_id}")
    return client


def _setup_announcements_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Distributed Computing",
        syllabus="Consensus, RPC, Fault Tolerance",
        schedule_info="Tue/Thu 14:00",
    )
    # Faculty
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA with announcement permission
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=201,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=True,
    )
    # TA without announcement permission
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=202,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=False,
    )
    # Student
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=301,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Observer
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=401,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_br_014_faculty_permitted_to_post_announcements(stub_iam):
    """Test ID: TC-BR-014.

    Source ID: BR-LMS-007 permitted (Faculty)
    Purpose: Verify that an assigned Faculty member is permitted to post
    course announcements.
    """
    _setup_announcements_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client_fac.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Midterm Exam Info",
            "content": "Midterm will cover Raft and Paxos.",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Midterm Exam Info"
    assert data["author_id"] == 101
    assert data["author_role"] == CourseRole.INSTRUCTOR


def test_tc_br_015_ta_with_permission_permitted_to_post(stub_iam):
    """Test ID: TC-BR-015.

    Source ID: BR-LMS-007 permitted (TA with permission)
    Purpose: Verify that an assigned TA is permitted to post course announcements
    when permission has been granted by Faculty.
    """
    _setup_announcements_world(101)
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client_ta.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Recitation Notes Posted",
            "content": "Recitation notes are uploaded in Materials.",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Recitation Notes Posted"
    assert data["author_id"] == 201
    assert data["author_role"] == CourseRole.TA


def test_tc_br_016_ta_without_permission_prohibited_from_posting(stub_iam):
    """Test ID: TC-BR-016.

    Source ID: BR-LMS-007 prohibited (TA without permission)
    Purpose: Verify that an assigned TA is prohibited from posting course
    announcements when permission has not been granted by Faculty.
    """
    _setup_announcements_world(101)
    client_ta2 = _make_client(
        stub_iam, user_id=202, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client_ta2.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Unauthorized Post",
            "content": "Should be rejected.",
        },
        format="json",
    )
    assert resp.status_code == 403


def test_tc_br_017_posted_announcement_timestamped_and_visible_course_wide(stub_iam):
    """Test ID: TC-BR-017.

    Source ID: BR-LMS-008 permitted
    Purpose: Verify that a posted announcement is recorded with a timestamp and
    is visible course-wide to all enrolled or linked users.
    """
    _setup_announcements_world(101)
    ann = CourseAnnouncement.objects.create(
        course_id=101,
        title="Project 1 Released",
        content="Project 1 is live on the assignment portal.",
        author_id=101,
        author_role=CourseRole.INSTRUCTOR,
    )

    authorized_users = [
        (101, _FACULTY, "faculty", "instructor"),
        (201, _TA, "student", "teaching_assistant"),
        (301, _STUDENT, "student", "student"),
        (401, _OBSERVER, "student", "course_observer"),
    ]

    for uid, perms, kind, role in authorized_users:
        client = _make_client(stub_iam, user_id=uid, perms=perms, kind=kind, role=role)
        resp = client.get("/api/v1/lms/announcements/?course_id=101")
        assert resp.status_code == 200
        announcements = resp.json()
        assert len(announcements) >= 1
        item = next((a for a in announcements if a["id"] == ann.id), None)
        assert item is not None
        assert item["title"] == "Project 1 Released"
        assert item["content"] == "Project 1 is live on the assignment portal."
        assert "created_at" in item
        assert item["created_at"] is not None


def test_tc_br_018_unassociated_users_prohibited_from_announcements(stub_iam):
    """Test ID: TC-BR-018.

    Source ID: BR-LMS-008 prohibited
    Purpose: Verify that course announcements are prohibited from being viewed
    by users who are not enrolled in or linked to the course.
    """
    _setup_announcements_world(101)
    CourseAnnouncement.objects.create(
        course_id=101,
        title="Confidential Course Notice",
        content="Internal announcement content",
        author_id=101,
        author_role=CourseRole.INSTRUCTOR,
    )

    # User U3 (user_id 777) has no enrollment or link to Course 101
    client_u3 = _make_client(
        stub_iam, user_id=777, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_u3.get("/api/v1/lms/announcements/?course_id=101")
    assert resp.status_code == 200
    assert resp.json() == []
