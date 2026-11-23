"""Specification use case tests for LMS Scheduled Content Release.

Covers:
- TC-UC-040 / UC-LMS-015 Main Flow: Scheduled content automatically transitioned to Published
- TC-UC-041 / UC-LMS-015 Alternative A1: Withdrawn content is not released
- TC-UC-042 / UC-LMS-015 Exception E1: Internal release failure handling
"""

import io
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
)
from modules.lms.registry import _STUDENT
from modules.lms.tasks import process_scheduled_content_release

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


def _setup_release_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Network Security",
        syllabus="Cryptography, Protocols, Firewalls",
        schedule_info="MWF 16:00",
    )
    # Faculty F1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
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


def test_tc_uc_040_scheduled_content_transitioned_to_published(stub_iam):
    """Test ID: TC-UC-040.

    Source ID: UC-LMS-015 Main Flow
    Purpose: Verify that scheduled content is automatically transitioned to
    Published/Available and made visible when its configured release time is reached.
    """
    _setup_release_world(101)
    now = timezone.now()
    past_release = now - timedelta(minutes=15)

    # Precondition: Material and Assignment are Scheduled with release time reached
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Scheduled Crypto Lecture",
        material_type=MaterialType.NOTE,
        content_text="RSA and Elliptic Curves",
        status=MaterialStatus.SCHEDULED,
        release_date=past_release,
        uploaded_by=101,
    )

    asg = Assignment.objects.create(
        course_id=101,
        title="Scheduled Lab 1",
        instructions="Implement AES encryption",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        release_date=past_release,
        status=AssignmentStatus.SCHEDULED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Before automated release: withheld from student
    assert client_s1.get(f"/api/v1/lms/materials/{mat.id}/").status_code == 404
    assert client_s1.get(f"/api/v1/lms/assignments/{asg.id}/").status_code == 404

    # Action: System executes scheduled content release task
    result = process_scheduled_content_release()
    assert result["materials_released"] >= 1
    assert result["assignments_released"] >= 1

    # Expected Result: Transitions to Published and visible to student
    mat.refresh_from_db()
    asg.refresh_from_db()
    assert mat.status == MaterialStatus.PUBLISHED
    assert asg.status == AssignmentStatus.PUBLISHED

    # Now visible to student
    resp_mat = client_s1.get(f"/api/v1/lms/materials/{mat.id}/")
    assert resp_mat.status_code == 200
    assert resp_mat.json()["title"] == "Scheduled Crypto Lecture"

    resp_asg = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_asg.status_code == 200
    assert resp_asg.json()["title"] == "Scheduled Lab 1"


def test_tc_uc_041_withdrawn_content_not_released(stub_iam):
    """Test ID: TC-UC-041.

    Source ID: UC-LMS-015 Alternative A1
    Purpose: Verify that no release occurs if scheduled content was withdrawn
    or unpublished before its release time.
    """
    _setup_release_world(101)
    now = timezone.now()
    past_release = now - timedelta(minutes=10)

    # Content configured for future release was withdrawn/unpublished back to DRAFT
    mat_withdrawn = CourseMaterial.objects.create(
        course_id=101,
        title="Withdrawn Material",
        material_type=MaterialType.NOTE,
        content_text="Confidential draft",
        status=MaterialStatus.DRAFT,
        release_date=past_release,
        uploaded_by=101,
    )

    asg_withdrawn = Assignment.objects.create(
        course_id=101,
        title="Withdrawn Assignment",
        instructions="Withdrawn instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        release_date=past_release,
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    # Action: Automated release evaluates scheduled releases
    result = process_scheduled_content_release()
    assert result["materials_released"] == 0
    assert result["assignments_released"] == 0

    # Expected: Content remains unpublished in DRAFT state
    mat_withdrawn.refresh_from_db()
    asg_withdrawn.refresh_from_db()
    assert mat_withdrawn.status == MaterialStatus.DRAFT
    assert asg_withdrawn.status == AssignmentStatus.DRAFT

    # Hidden from student
    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_s1.get(f"/api/v1/lms/materials/{mat_withdrawn.id}/").status_code == 404
    assert client_s1.get(f"/api/v1/lms/assignments/{asg_withdrawn.id}/").status_code == 404


def test_tc_uc_042_release_processing_failure_handling(stub_iam):
    """Test ID: TC-UC-042.

    Source ID: UC-LMS-015 Exception E1
    Purpose: Verify that if release processing encounters a failure, content
    remains unavailable and the failure is recorded for operational handling.
    """
    _setup_release_world(101)
    now = timezone.now()
    past_release = now - timedelta(minutes=30)

    # Content ITEM_err in Scheduled state with release time reached
    mat_err = CourseMaterial.objects.create(
        course_id=101,
        title="Unreleased Due To Error",
        material_type=MaterialType.NOTE,
        content_text="Material blocked by failure",
        status=MaterialStatus.SCHEDULED,
        release_date=past_release,
        uploaded_by=101,
    )

    # Simulate internal database failure during state transition
    with patch(
        "modules.lms.tasks.CourseMaterial.objects.filter",
        side_effect=DatabaseError("Simulated database failure during release transition"),
    ), pytest.raises(DatabaseError):
        process_scheduled_content_release()

    # Content remains unavailable and unexposed to students
    mat_err.refresh_from_db()
    assert mat_err.status == MaterialStatus.SCHEDULED

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_s1.get(f"/api/v1/lms/materials/{mat_err.id}/").status_code == 404

    # System operational check records the failure (overdue unreleased items)
    out = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("lms_work_status", stdout=out)
    assert exc.value.code == 1
    assert "past release_date" in out.getvalue()
