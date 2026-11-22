"""Specification use case tests for LMS Course Workspace management.

Covers:
- TC-UC-001 / UC-LMS-001 Main Flow: Access Course Workspace
- TC-UC-002 / UC-LMS-001 Alternative A1: Unauthorized user denied workspace access
- TC-UC-003 / UC-LMS-001 Exception E1: Course workspace access when registration data unavailable
- TC-UC-004 / UC-LMS-002 Main Flow: Faculty configures course workspace details
- TC-UC-005 / UC-LMS-002 Alternative A1: Faculty edits previously published course details
- TC-UC-006 / UC-LMS-002 Exception E1: Unauthorized Faculty cannot configure course details
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


def _setup_workspace_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Software Engineering",
        syllabus="Initial syllabus content",
        schedule_info="MWF 10:00-11:00",
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
    )
    # Student S1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=301,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_uc_001_authorized_user_accesses_workspace(stub_iam):
    """Test ID: TC-UC-001.

    Source ID: UC-LMS-001 Main Flow
    Purpose: Verify that an authorized user can access the dedicated course
    workspace and view syllabus, schedule, instructor(s), and TA(s).
    """
    _setup_workspace_world(101)
    client = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client.get("/api/v1/lms/courses/101/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["course_id"] == 101
    assert data["course_code"] == "CS101"
    assert data["title"] == "Software Engineering"
    assert data["syllabus"] == "Initial syllabus content"
    assert data["schedule_info"] == "MWF 10:00-11:00"
    assert 101 in data["instructors"]
    assert 201 in data["teaching_assistants"]


def test_tc_uc_002_unauthorized_user_denied_workspace_access(stub_iam):
    """Test ID: TC-UC-002.

    Source ID: UC-LMS-001 Alternative A1
    Purpose: Verify that access to the course workspace is denied when the
    requesting user is not authorized for the selected course.
    """
    _setup_workspace_world(101)
    # User U2 (ID: 999) has student permissions but no membership in Course 101
    client = _make_client(
        stub_iam, user_id=999, perms=_STUDENT, kind="student", role="student"
    )

    resp = client.get("/api/v1/lms/courses/101/")
    # Denied access through concealment per api conventions (404 Not Found)
    assert resp.status_code == 404
    error_msg = resp.json().get("error", {}).get("message", "")
    assert "not found or access denied" in error_msg.lower()


def test_tc_uc_003_workspace_hidden_when_registration_data_unavailable(stub_iam):
    """Test ID: TC-UC-003.

    Source ID: UC-LMS-001 Exception E1
    Purpose: Verify that the system does not expose the course workspace when
    authoritative registration or association data are unavailable.
    """
    # Course exists, but authoritative registration data has no confirmed active membership for U1
    CourseWorkspace.objects.create(
        course_id=101,
        course_code="CS101",
        title="Software Engineering",
        syllabus="Confidential Syllabus",
        schedule_info="MWF 10:00",
    )
    # User U1 is authenticated in Fusion, but registration data is absent/unavailable
    client = _make_client(
        stub_iam, user_id=555, perms=_STUDENT, kind="student", role="student"
    )

    resp = client.get("/api/v1/lms/courses/101/")
    assert resp.status_code == 404
    error_msg = resp.json().get("error", {}).get("message", "")
    assert "not found or access denied" in error_msg.lower()


def test_tc_uc_004_assigned_faculty_configures_workspace(stub_iam):
    """Test ID: TC-UC-004.

    Source ID: UC-LMS-002 Main Flow
    Purpose: Verify that assigned Faculty can configure course workspace details
    and save/publish the changes.
    """
    _setup_workspace_world(101)
    client = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    new_syllabus = "Updated Syllabus: Advanced System Design"
    new_schedule = "Tue/Thu 14:00-15:30"
    resp = client.patch(
        "/api/v1/lms/courses/101/",
        data={
            "syllabus": new_syllabus,
            "schedule_info": new_schedule,
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["syllabus"] == new_syllabus
    assert data["schedule_info"] == new_schedule

    # Verify updated details in course workspace
    get_resp = client.get("/api/v1/lms/courses/101/")
    assert get_resp.status_code == 200
    assert get_resp.json()["syllabus"] == new_syllabus
    assert get_resp.json()["schedule_info"] == new_schedule


def test_tc_uc_005_assigned_faculty_edits_published_details(stub_iam):
    """Test ID: TC-UC-005.

    Source ID: UC-LMS-002 Alternative A1
    Purpose: Verify that assigned Faculty can edit previously published course details.
    """
    _setup_workspace_world(101)
    client = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    # First configuration
    client.patch(
        "/api/v1/lms/courses/101/",
        data={"syllabus": "Version 1", "schedule_info": "Mon 10:00"},
        format="json",
    )

    # Edit previously published course details
    updated_syllabus = "Version 2: Expanded syllabus description"
    updated_schedule = "Mon/Wed 10:00-11:30"
    resp_edit = client.patch(
        "/api/v1/lms/courses/101/",
        data={
            "syllabus": updated_syllabus,
            "schedule_info": updated_schedule,
        },
        format="json",
    )
    assert resp_edit.status_code == 200
    assert resp_edit.json()["syllabus"] == updated_syllabus
    assert resp_edit.json()["schedule_info"] == updated_schedule

    # Verify persisted in database
    ws = CourseWorkspace.objects.get(course_id=101)
    assert ws.syllabus == updated_syllabus
    assert ws.schedule_info == updated_schedule


def test_tc_uc_006_unauthorized_faculty_configuration_rejected(stub_iam):
    """Test ID: TC-UC-006.

    Source ID: UC-LMS-002 Exception E1
    Purpose: Verify that course details configuration is rejected for an
    unauthorized Faculty member not assigned to the course.
    """
    ws = _setup_workspace_world(101)
    initial_syllabus = ws.syllabus
    initial_schedule = ws.schedule_info

    # Faculty F2 (user_id 888) is not assigned to Course 101
    client = _make_client(
        stub_iam, user_id=888, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client.patch(
        "/api/v1/lms/courses/101/",
        data={
            "syllabus": "Hacked Syllabus",
            "schedule_info": "Never",
        },
        format="json",
    )
    # Refused per api-conventions (403 Forbidden)
    assert resp.status_code == 403

    # Existing course details remain unchanged
    ws.refresh_from_db()
    assert ws.syllabus == initial_syllabus
    assert ws.schedule_info == initial_schedule
