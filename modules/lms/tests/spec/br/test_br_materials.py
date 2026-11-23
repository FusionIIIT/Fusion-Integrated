"""Specification business rule tests for LMS Course Materials visibility and scheduling.

Covers:
- TC-BR-010 / BR-LMS-005 permitted: Published materials visible in read-only form
- TC-BR-011 / BR-LMS-005 prohibited: Unpublished draft materials remain invisible
- TC-BR-012 / BR-LMS-006 permitted: Scheduled material becomes available at release time
- TC-BR-013 / BR-LMS-006 prohibited: Future-dated scheduled material remains unavailable
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


def _setup_materials_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Operating Systems",
        syllabus="Kernel architecture",
        schedule_info="MWF 11:00",
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


def test_tc_br_010_published_materials_visible_read_only(stub_iam):
    """Test ID: TC-BR-010.

    Source ID: BR-LMS-005 permitted
    Purpose: Verify that course materials that are published and released are
    visible to enrolled students in read-only form.
    """
    _setup_materials_world(101)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Published Kernel Overview",
        material_type=MaterialType.NOTE,
        content_text="Intro to monolithic kernels",
        section_name="Week 1",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # 1. List materials
    resp_list = client_s1.get("/api/v1/lms/materials/?course_id=101")
    assert resp_list.status_code == 200
    assert any(m["id"] == mat.id for m in resp_list.json())

    # 2. Retrieve detail
    resp_detail = client_s1.get(f"/api/v1/lms/materials/{mat.id}/")
    assert resp_detail.status_code == 200
    data = resp_detail.json()
    assert data["id"] == mat.id
    assert data["title"] == "Published Kernel Overview"
    assert data["content_text"] == "Intro to monolithic kernels"

    # 3. Read-only verification: Student write attempt refused
    resp_patch = client_s1.patch(
        f"/api/v1/lms/materials/{mat.id}/",
        data={"title": "Hacked Title"},
        format="json",
    )
    assert resp_patch.status_code == 403


def test_tc_br_011_unpublished_materials_remain_invisible(stub_iam):
    """Test ID: TC-BR-011.

    Source ID: BR-LMS-005 prohibited
    Purpose: Verify that course materials that are unpublished remain invisible
    and withheld from students.
    """
    _setup_materials_world(101)
    mat_draft = CourseMaterial.objects.create(
        course_id=101,
        title="Unpublished Draft Material",
        material_type=MaterialType.NOTE,
        content_text="Confidential notes",
        section_name="Week 2",
        status=MaterialStatus.DRAFT,
        uploaded_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Omitted from materials list
    resp_list = client_s1.get("/api/v1/lms/materials/?course_id=101")
    assert resp_list.status_code == 200
    returned_ids = [m["id"] for m in resp_list.json()]
    assert mat_draft.id not in returned_ids

    # Detail access denied
    resp_detail = client_s1.get(f"/api/v1/lms/materials/{mat_draft.id}/")
    assert resp_detail.status_code == 404


def test_tc_br_012_scheduled_material_available_at_release_time(stub_iam):
    """Test ID: TC-BR-012.

    Source ID: BR-LMS-006 permitted
    Purpose: Verify that scheduled course material becomes available and
    visible to students once its configured release date/time is reached.
    """
    _setup_materials_world(101)
    now = timezone.now()
    past_release = now - timedelta(minutes=5)

    mat_sched = CourseMaterial.objects.create(
        course_id=101,
        title="Ready to Release Material",
        material_type=MaterialType.NOTE,
        content_text="Released material content",
        status=MaterialStatus.SCHEDULED,
        release_date=past_release,
        uploaded_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Before background sweep
    assert client_s1.get(f"/api/v1/lms/materials/{mat_sched.id}/").status_code == 404

    # Run release sweep
    res = process_scheduled_content_release()
    assert res["materials_released"] >= 1

    # Now available
    mat_sched.refresh_from_db()
    assert mat_sched.status == MaterialStatus.PUBLISHED

    resp = client_s1.get(f"/api/v1/lms/materials/{mat_sched.id}/")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Ready to Release Material"


def test_tc_br_013_future_scheduled_material_remains_unavailable(stub_iam):
    """Test ID: TC-BR-013.

    Source ID: BR-LMS-006 prohibited
    Purpose: Verify that course material configured with a future release date
    remains unavailable prior to the configured release date/time.
    """
    _setup_materials_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=5)

    mat_future = CourseMaterial.objects.create(
        course_id=101,
        title="Future Release Material",
        material_type=MaterialType.NOTE,
        content_text="Not yet available",
        status=MaterialStatus.SCHEDULED,
        release_date=future_release,
        uploaded_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Omitted from list
    resp_list = client_s1.get("/api/v1/lms/materials/?course_id=101")
    assert resp_list.status_code == 200
    returned_ids = [m["id"] for m in resp_list.json()]
    assert mat_future.id not in returned_ids

    # Detail access returns 404
    resp_detail = client_s1.get(f"/api/v1/lms/materials/{mat_future.id}/")
    assert resp_detail.status_code == 404
