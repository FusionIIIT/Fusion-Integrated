"""Tests asserting PATCH permissions on CourseWorkspace (R1-14)."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import CourseRole, MembershipStatus
from modules.lms.models import CourseMembership, CourseWorkspace

pytestmark = pytest.mark.django_db


def test_patch_course_without_workspace_update_permission_returns_403(stub_iam):
    course_id = 901
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS901",
        title="Distributed Systems",
        syllabus="Initial syllabus",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=5001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )

    # Student has lms.workspace.view but lacks lms.workspace.update
    stub_iam(
        make_session(
            user_id=5001,
            kind="student",
            permissions=("lms.workspace.view",),
            modules=("lms",),
        )
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    res = client.patch(
        f"/api/v1/lms/courses/{course_id}/",
        data={"syllabus": "Modified by student"},
        format="json",
    )
    assert res.status_code == 403


def test_patch_course_with_workspace_update_permission_returns_200(stub_iam):
    course_id = 902
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS902",
        title="Cloud Computing",
        syllabus="Initial syllabus",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=4001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )

    # Instructor has lms.workspace.update
    stub_iam(
        make_session(
            user_id=4001,
            kind="faculty",
            permissions=("lms.workspace.view", "lms.workspace.update"),
            modules=("lms",),
        )
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    res = client.patch(
        f"/api/v1/lms/courses/{course_id}/",
        data={"syllabus": "Updated syllabus: Consensus & Paxos", "schedule_info": "Mon/Wed 2 PM"},
        format="json",
    )
    assert res.status_code == 200
    assert res.data["syllabus"] == "Updated syllabus: Consensus & Paxos"
    assert res.data["schedule_info"] == "Mon/Wed 2 PM"
