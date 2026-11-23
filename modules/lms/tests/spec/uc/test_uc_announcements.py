"""Specification use case tests for LMS Course Announcements management.

Covers:
- TC-UC-013 / UC-LMS-005 Main Flow: Faculty posts course announcement
- TC-UC-014 / UC-LMS-005 Alternative A1: TA posts course announcement
- TC-UC-015 / UC-LMS-005 Exception E1: Unauthorized announcement posting rejected
- TC-UC-016 / UC-LMS-006 Main Flow: Authorized user views announcements with timestamps
- TC-UC-017 / UC-LMS-006 Exception E1: Unauthorized user denied access to announcements
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
        title="Operating Systems",
        syllabus="Processes, Threads, Virtual Memory",
        schedule_info="Tue/Thu 13:00",
    )
    # Faculty F1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA T1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=201,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=True,
    )
    # Student S1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=301,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Observer O1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=401,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_uc_013_faculty_posts_announcement(stub_iam):
    """Test ID: TC-UC-013.

    Source ID: UC-LMS-005 Main Flow
    Purpose: Verify that assigned Faculty can post a timestamped course-wide announcement.
    """
    _setup_announcements_world(101)
    client = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Exam Schedule Released",
            "content": "Midterm will take place in Room 402.",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Exam Schedule Released"
    assert data["content"] == "Midterm will take place in Room 402."
    assert data["author_id"] == 101
    assert data["author_role"] == CourseRole.INSTRUCTOR
    assert "created_at" in data
    assert data["created_at"] is not None

    # Visible course-wide to enrolled/linked student
    student_client = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = student_client.get("/api/v1/lms/announcements/?course_id=101")
    assert resp_student.status_code == 200
    ann_ids = [a["id"] for a in resp_student.json()]
    assert data["id"] in ann_ids


def test_tc_uc_014_ta_posts_announcement(stub_iam):
    """Test ID: TC-UC-014.

    Source ID: UC-LMS-005 Alternative A1
    Purpose: Verify that a Teaching Assistant (TA) can post a course announcement
    when permitted by Faculty.
    """
    _setup_announcements_world(101)
    # TA T1 has lms.announcement.create permission in _TA
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client_ta.post(
        "/api/v1/lms/announcements/",
        data={
            "course_id": 101,
            "title": "Office Hours Moved",
            "content": "Today's TA office hours are shifted to 16:00.",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Office Hours Moved"
    assert data["content"] == "Today's TA office hours are shifted to 16:00."
    assert data["author_id"] == 201
    assert data["author_role"] == CourseRole.TA
    assert "created_at" in data

    # Visible in DB
    ann = CourseAnnouncement.objects.get(id=data["id"])
    assert ann.author_role == CourseRole.TA


def test_tc_uc_015_unauthorized_announcement_posting_rejected(stub_iam):
    """Test ID: TC-UC-015.

    Source ID: UC-LMS-005 Exception E1
    Purpose: Verify that announcement posting attempts by unauthorized users
    (Student, Observer, or TA without permission) are rejected.
    """
    _setup_announcements_world(101)
    initial_count = CourseAnnouncement.objects.filter(course_id=101).count()

    # 1. Student attempting to post
    student_client = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = student_client.post(
        "/api/v1/lms/announcements/",
        data={"course_id": 101, "title": "Student Post", "content": "Text"},
        format="json",
    )
    assert resp_student.status_code == 403

    # 2. Observer attempting to post
    obs_client = _make_client(
        stub_iam, user_id=401, perms=_OBSERVER, kind="student", role="course_observer"
    )
    resp_obs = obs_client.post(
        "/api/v1/lms/announcements/",
        data={"course_id": 101, "title": "Observer Post", "content": "Text"},
        format="json",
    )
    assert resp_obs.status_code == 403

    # 3. TA without announcement posting permission
    # Create TA T2 without can_post_announcement
    CourseMembership.objects.create(
        course_id=101,
        user_id=202,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=False,
    )
    ta_no_perm_client = _make_client(
        stub_iam,
        user_id=202,
        perms=_TA,
        kind="student",
        role="teaching_assistant",
    )
    resp_ta = ta_no_perm_client.post(
        "/api/v1/lms/announcements/",
        data={"course_id": 101, "title": "TA No Perm", "content": "Text"},
        format="json",
    )
    assert resp_ta.status_code == 403

    # Preserves no announcements stored
    assert CourseAnnouncement.objects.filter(course_id=101).count() == initial_count


def test_tc_uc_016_authorized_user_views_announcements_with_timestamps(stub_iam):
    """Test ID: TC-UC-016.

    Source ID: UC-LMS-006 Main Flow
    Purpose: Verify that an authorized user can view course announcements
    displayed with timestamps.
    """
    _setup_announcements_world(101)
    ann = CourseAnnouncement.objects.create(
        course_id=101,
        title="Welcome to Operating Systems",
        content="Welcome students to the course.",
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
        matched = next((a for a in announcements if a["id"] == ann.id), None)
        assert matched is not None
        assert matched["title"] == "Welcome to Operating Systems"
        assert matched["content"] == "Welcome students to the course."
        assert "created_at" in matched
        assert matched["created_at"] is not None


def test_tc_uc_017_unauthorized_user_denied_announcements(stub_iam):
    """Test ID: TC-UC-017.

    Source ID: UC-LMS-006 Exception E1
    Purpose: Verify that an unauthorized user not enrolled in or linked to the
    course is denied access to course announcements.
    """
    _setup_announcements_world(101)
    CourseAnnouncement.objects.create(
        course_id=101,
        title="Classified Course Announcement",
        content="Restricted announcement info",
        author_id=101,
        author_role=CourseRole.INSTRUCTOR,
    )

    # User U_unauth (user_id 777) is not enrolled or linked to Course 101
    client_unauth = _make_client(
        stub_iam, user_id=777, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_unauth.get("/api/v1/lms/announcements/?course_id=101")
    assert resp.status_code == 200
    # No announcement content exposed
    assert resp.json() == []
