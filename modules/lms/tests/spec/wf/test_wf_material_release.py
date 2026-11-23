"""Basis Workflow BW-LMS-01: Scheduled Course Material Release.

Covers:
- TC-WF-001 / BW-LMS-01 step-1-success: Material transitions Draft -> Scheduled
- TC-WF-002 / BW-LMS-01 step-2-holding-guard: Scheduled material remains withheld prior to release
- TC-WF-003 / BW-LMS-01 step-2-success: Scheduled material transitions to Published at release time
- TC-WF-004 / BW-LMS-01 full-path: End-to-end scheduled material release workflow
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import (
    CourseRole,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
)
from modules.lms.models import CourseMaterial, CourseMembership, CourseWorkspace
from modules.lms.registry import _FACULTY, _STUDENT
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


def _setup_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Distributed Systems",
        syllabus="Syllabus",
        schedule_info="MWF 10:00",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=301,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_wf_001_step_1_material_draft_to_scheduled(stub_iam):
    """Test ID: TC-WF-001.

    Source ID: BW-LMS-01 step-1-success
    Purpose: Verify transition from Material Draft / Unpublished to Material
    Scheduled when Faculty configures a valid future release date.
    """
    _setup_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    future_release = now + timedelta(days=3)

    resp = client_fac.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Scheduled Lecture Notes",
            "material_type": MaterialType.NOTE,
            "content_text": "Content for future release",
            "release_date": future_release.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == MaterialStatus.SCHEDULED
    mat = CourseMaterial.objects.get(id=data["id"])
    assert mat.status == MaterialStatus.SCHEDULED

    # Withheld from students
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_stu = client_stu.get(f"/api/v1/lms/materials/{mat.id}/")
    assert resp_stu.status_code == 404


def test_tc_wf_002_step_2_holding_guard_scheduled_material(stub_iam):
    """Test ID: TC-WF-002.

    Source ID: BW-LMS-01 step-2-holding-guard
    Purpose: Verify that course material in Material Scheduled state remains
    unpublished while current system time has not reached the configured release timestamp.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=2)

    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Midterm Review Notes",
        material_type=MaterialType.NOTE,
        content_text="Confidential until release",
        status=MaterialStatus.SCHEDULED,
        release_date=future_release,
        uploaded_by=101,
    )

    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # 1. Student queries materials list: material is omitted
    resp_list = client_stu.get("/api/v1/lms/materials/?course_id=101")
    assert resp_list.status_code == 200
    returned_ids = [m["id"] for m in resp_list.json()]
    assert mat.id not in returned_ids

    # 2. Student queries detail: returns 404
    resp_detail = client_stu.get(f"/api/v1/lms/materials/{mat.id}/")
    assert resp_detail.status_code == 404

    # 3. Scheduled task executes before release date: holding guard preserves SCHEDULED state
    res = process_scheduled_content_release()
    assert res["materials_released"] == 0

    mat.refresh_from_db()
    assert mat.status == MaterialStatus.SCHEDULED


def test_tc_wf_003_step_2_success_material_scheduled_to_published(stub_iam):
    """Test ID: TC-WF-003.

    Source ID: BW-LMS-01 step-2-success
    Purpose: Verify transition from Material Scheduled to Material Published / Available
    when the configured release time is reached.
    """
    _setup_world(101)
    now = timezone.now()
    past_release = now - timedelta(minutes=10)

    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Week 1 Slides",
        material_type=MaterialType.NOTE,
        content_text="Intro slides",
        status=MaterialStatus.SCHEDULED,
        release_date=past_release,
        uploaded_by=101,
    )

    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Prior to release task
    assert client_stu.get(f"/api/v1/lms/materials/{mat.id}/").status_code == 404

    # Process release
    res = process_scheduled_content_release()
    assert res["materials_released"] >= 1

    # Transitioned to Published / Available
    mat.refresh_from_db()
    assert mat.status == MaterialStatus.PUBLISHED

    resp_stu = client_stu.get(f"/api/v1/lms/materials/{mat.id}/")
    assert resp_stu.status_code == 200
    assert resp_stu.json()["title"] == "Week 1 Slides"


def test_tc_wf_004_full_path_scheduled_material_release(stub_iam):
    """Test ID: TC-WF-004.

    Source ID: BW-LMS-01 full-path
    Purpose: Verify the complete end-to-end scheduled course material release
    basis workflow from Faculty scheduling through automatic system release at the configured time.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=2)

    # Step 1: Faculty schedules material with future release date
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_create = client_fac.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Full Path Material",
            "material_type": MaterialType.NOTE,
            "content_text": "Full path content",
            "release_date": future_release.isoformat(),
        },
        format="json",
    )
    assert resp_create.status_code == 201
    mat_id = resp_create.json()["id"]

    mat = CourseMaterial.objects.get(id=mat_id)
    assert mat.status == MaterialStatus.SCHEDULED

    # Step 2 (holding): While current time < release time, material is inaccessible to student
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/materials/{mat_id}/").status_code == 404

    # Step 3 (release): Clock reaches release time, background sweep runs
    mat.release_date = now - timedelta(minutes=1)
    mat.save(update_fields=["release_date"])

    res = process_scheduled_content_release()
    assert res["materials_released"] >= 1

    mat.refresh_from_db()
    assert mat.status == MaterialStatus.PUBLISHED

    # Successfully completes workflow: student can now view material
    resp_stu = client_stu.get(f"/api/v1/lms/materials/{mat_id}/")
    assert resp_stu.status_code == 200
    assert resp_stu.json()["title"] == "Full Path Material"
