"""Specification tests for LMS Course Announcements functional requirements.

Covers:
- TC-FR-013 / AFR-LMS-005.1: Faculty posts announcement (CFR-LMS-005)
- TC-FR-014 / AFR-LMS-005.2: Permitted TA posts announcement (CFR-LMS-005)
- TC-FR-015 / AFR-LMS-005.3: Timestamp announcement (CFR-LMS-005)
- TC-FR-016 / AFR-LMS-005.4: Make announcement course-wide (CFR-LMS-005)
"""

from datetime import timedelta

import pytest
from django.utils import timezone
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


def _setup_course(course_id: int = 101):
    return CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"C{course_id}",
        title="Intro to Computing",
    )


def test_tc_fr_013_faculty_posts_announcement(stub_iam):
    """Test ID: TC-FR-013.

    Source ID: AFR-LMS-005.1: Faculty posts announcement (CFR-LMS-005)
    Purpose: Verify that Faculty can post a course-wide announcement for an
    assigned course.
    """
    _setup_course(101)
    CourseMembership.objects.create(
        course_id=101,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )

    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    resp = client.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Exam Date Update",
            "content": "Midterm is on Friday",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Exam Date Update"
    assert data["content"] == "Midterm is on Friday"

    # Verify persistence
    ann = CourseAnnouncement.objects.get(id=data["id"])
    assert ann.title == "Exam Date Update"
    assert ann.content == "Midterm is on Friday"
    assert ann.author_id == 2001
    assert ann.author_role == CourseRole.INSTRUCTOR


def test_tc_fr_014_permitted_ta_posts_announcement(stub_iam):
    """Test ID: TC-FR-014.

    Source ID: AFR-LMS-005.2: Permitted TA posts announcement (CFR-LMS-005)
    Purpose: Verify that a TA can post course announcements only when permitted,
    and is restricted when permission is not granted.
    """
    _setup_course(101)
    # TA1: restricted (can_post_announcement=False)
    CourseMembership.objects.create(
        course_id=101,
        user_id=3001,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=False,
    )
    # TA2: permitted (can_post_announcement=True)
    CourseMembership.objects.create(
        course_id=101,
        user_id=3002,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=True,
    )

    # TA1 attempts to post announcement -> blocked
    ta1_client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp_ta1 = ta1_client.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Unauthorized TA Announcement",
            "content": "This should fail",
        },
        format="json",
    )
    assert resp_ta1.status_code == 403

    # TA2 posts announcement -> allowed
    ta2_client = _make_client(
        stub_iam, user_id=3002, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp_ta2 = ta2_client.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Permitted TA Announcement",
            "content": "Office hours shifted to 4 PM.",
        },
        format="json",
    )
    assert resp_ta2.status_code == 201
    assert CourseAnnouncement.objects.filter(author_id=3002).exists()


def test_tc_fr_015_timestamp_announcement(stub_iam):
    """Test ID: TC-FR-015.

    Source ID: AFR-LMS-005.3: Timestamp announcement (CFR-LMS-005)
    Purpose: Verify that the system records a timestamp for each posted course
    announcement.
    """
    _setup_course(101)
    CourseMembership.objects.create(
        course_id=101,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )

    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    before_post = timezone.now()
    resp = client.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Welcome to Class",
            "content": "Welcome students to the semester.",
        },
        format="json",
    )
    after_post = timezone.now()

    assert resp.status_code == 201
    data = resp.json()
    assert "created_at" in data
    assert data["created_at"] is not None

    ann = CourseAnnouncement.objects.get(id=data["id"])
    assert before_post - timedelta(seconds=2) <= ann.created_at <= after_post + timedelta(seconds=2)


def test_tc_fr_016_make_announcement_course_wide(stub_iam):
    """Test ID: TC-FR-016.

    Source ID: AFR-LMS-005.4: Make announcement course-wide (CFR-LMS-005)
    Purpose: Verify that a posted announcement is visible to all users enrolled
    in or linked to the course (Students, TAs, Observers).
    """
    _setup_course(101)
    # Student S1
    CourseMembership.objects.create(
        course_id=101,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # TA1
    CourseMembership.objects.create(
        course_id=101,
        user_id=3001,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
    )
    # Observer O1
    CourseMembership.objects.create(
        course_id=101,
        user_id=4001,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )

    ann = CourseAnnouncement.objects.create(
        course_id=101,
        title="Course-wide Notice A1",
        content="Important schedule update for all participants.",
        author_id=2001,
        author_role=CourseRole.INSTRUCTOR,
    )

    # 1. Student S1 views announcements
    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    stu_resp = stu_client.get("/api/v1/lms/announcements/?course_id=101")
    assert stu_resp.status_code == 200
    assert any(a["id"] == ann.id for a in stu_resp.json())

    # 2. TA1 views announcements
    ta_client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )
    ta_resp = ta_client.get("/api/v1/lms/announcements/?course_id=101")
    assert ta_resp.status_code == 200
    assert any(a["id"] == ann.id for a in ta_resp.json())

    # 3. Observer O1 views announcements
    obs_client = _make_client(
        stub_iam, user_id=4001, perms=_OBSERVER, kind="student", role="course_observer"
    )
    obs_resp = obs_client.get("/api/v1/lms/announcements/?course_id=101")
    assert obs_resp.status_code == 200
    assert any(a["id"] == ann.id for a in obs_resp.json())
