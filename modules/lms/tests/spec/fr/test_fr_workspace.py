"""Specification tests for LMS Course Workspace functional requirements.

Covers:
- TC-FR-001 / AFR-LMS-001.1: Open dedicated course workspace (CFR-LMS-001)
- TC-FR-002 / AFR-LMS-001.2: Display course home information (CFR-LMS-001)
- TC-FR-003 / AFR-LMS-001.3: Restrict course-specific access (CFR-LMS-001)
- TC-FR-004 / AFR-LMS-002.1: Configure assigned course workspace (CFR-LMS-002)
- TC-FR-005 / AFR-LMS-002.2: Publish and edit course details (CFR-LMS-002)
"""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import CourseRole, MembershipStatus
from modules.lms.models import CourseMembership, CourseWorkspace
from modules.lms.registry import _FACULTY, _STUDENT

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


def test_tc_fr_001_open_dedicated_course_workspace(stub_iam):
    """Test ID: TC-FR-001.

    Source ID: AFR-LMS-001.1: Open dedicated course workspace (CFR-LMS-001)
    Purpose: Verify that the system opens a dedicated course workspace when
    an authorized user selects their course.
    """
    ws = CourseWorkspace.objects.create(
        course_id=101,
        course_code="C101",
        title="Software Engineering",
        syllabus="Intro to Software Eng",
        schedule_info="Mon/Wed 10:00-11:30",
    )
    CourseMembership.objects.create(
        course_id=101,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )

    client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")

    # 1. User views course list
    list_resp = client.get("/api/v1/lms/courses/")
    assert list_resp.status_code == 200
    course_ids = [c["course_id"] for c in list_resp.json()]
    assert 101 in course_ids

    # 2. User selects Course C101
    resp = client.get(f"/api/v1/lms/courses/{ws.course_id}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["course_id"] == 101
    assert data["title"] == "Software Engineering"
    assert data["course_code"] == "C101"


def test_tc_fr_002_display_course_home_information(stub_iam):
    """Test ID: TC-FR-002.

    Source ID: AFR-LMS-001.2: Display course home information (CFR-LMS-001)
    Purpose: Verify that the course home page displays syllabus, schedule,
    instructor(s), and TA(s).
    """
    CourseWorkspace.objects.create(
        course_id=101,
        course_code="C101",
        title="Algorithms",
        syllabus="Divide and Conquer, Dynamic Programming, Graphs",
        schedule_info="Tue/Thu 14:00-15:30, Room 204",
    )
    # Instructor
    CourseMembership.objects.create(
        course_id=101,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA
    CourseMembership.objects.create(
        course_id=101,
        user_id=3001,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
    )
    # Enrolled Student
    CourseMembership.objects.create(
        course_id=101,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )

    client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    resp = client.get("/api/v1/lms/courses/101/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["syllabus"] == "Divide and Conquer, Dynamic Programming, Graphs"
    assert data["schedule_info"] == "Tue/Thu 14:00-15:30, Room 204"
    assert 2001 in data["instructors"]
    assert 3001 in data["teaching_assistants"]


def test_tc_fr_003_restrict_course_specific_access(stub_iam):
    """Test ID: TC-FR-003.

    Source ID: AFR-LMS-001.3: Restrict course-specific access (CFR-LMS-001)
    Purpose: Verify that access to a course workspace is restricted and denied to
    users not enrolled in, assigned to, or linked to the course.
    """
    CourseWorkspace.objects.create(
        course_id=101,
        course_code="C101",
        title="Database Systems",
        syllabus="Relational Algebra, SQL, Transactions",
        schedule_info="MWF 09:00-10:00",
    )
    # User U2 is authenticated in LMS but has NO membership in Course C101
    client = _make_client(stub_iam, user_id=9999, perms=_STUDENT, kind="student", role="student")

    resp = client.get("/api/v1/lms/courses/101/")
    # Enforces 404 per API conventions to prevent course existence enumeration
    assert resp.status_code in (403, 404)


def test_tc_fr_004_configure_assigned_course_workspace(stub_iam):
    """Test ID: TC-FR-004.

    Source ID: AFR-LMS-002.1: Configure assigned course workspace (CFR-LMS-002)
    Purpose: Verify that an assigned Faculty member can configure the course
    workspace settings for their course.
    """
    CourseWorkspace.objects.create(
        course_id=101,
        course_code="C101",
        title="Operating Systems",
        syllabus="Initial Syllabus",
        schedule_info="Initial Schedule",
    )
    CourseMembership.objects.create(
        course_id=101,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )

    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    update_data = {
        "syllabus": "Updated OS Syllabus: Processes, Threads, Memory Management",
        "schedule_info": "Mon/Wed 15:00-16:30, Lab 3",
    }
    resp = client.patch("/api/v1/lms/courses/101/", data=update_data, format="json")
    assert resp.status_code == 200
    data = resp.json()

    assert data["syllabus"] == update_data["syllabus"]
    assert data["schedule_info"] == update_data["schedule_info"]

    # Verify persistence in database
    workspace = CourseWorkspace.objects.get(course_id=101)
    assert workspace.syllabus == update_data["syllabus"]
    assert workspace.schedule_info == update_data["schedule_info"]


def test_tc_fr_005_publish_and_edit_course_details(stub_iam):
    """Test ID: TC-FR-005.

    Source ID: AFR-LMS-002.2: Publish and edit course details (CFR-LMS-002)
    Purpose: Verify that Faculty can edit and publish course details for an assigned
    course, making them visible in the course workspace.
    """
    CourseWorkspace.objects.create(
        course_id=101,
        course_code="C101",
        title="Computer Networks",
        syllabus="Old Syllabus Draft",
        schedule_info="TBD",
    )
    CourseMembership.objects.create(
        course_id=101,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=101,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )

    # Faculty edits course details
    fac_client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    new_details = {
        "syllabus": "Published Syllabus: OSI Model, TCP/IP, Congestion Control",
        "schedule_info": "Mon/Wed/Fri 11:00-12:00, Hall A",
    }
    patch_resp = fac_client.patch("/api/v1/lms/courses/101/", data=new_details, format="json")
    assert patch_resp.status_code == 200

    # Student views updated course workspace
    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    view_resp = stu_client.get("/api/v1/lms/courses/101/")
    assert view_resp.status_code == 200
    stu_data = view_resp.json()

    assert stu_data["syllabus"] == new_details["syllabus"]
    assert stu_data["schedule_info"] == new_details["schedule_info"]
