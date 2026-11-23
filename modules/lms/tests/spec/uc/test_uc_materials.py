"""Specification use case tests for LMS Course Materials management.

Covers:
- TC-UC-007 / UC-LMS-003 Main Flow: Faculty adds course material and publishes immediately
- TC-UC-008 / UC-LMS-003 Alternative A1: Faculty edits and reorganizes existing materials
- TC-UC-009 / UC-LMS-003 Exception E1: Non-Faculty material write attempts rejected
- TC-UC-010 / UC-LMS-004 Main Flow: Authorized course user views published materials
- TC-UC-011 / UC-LMS-004 Alternative A1: Scheduled or unpublished materials omitted from students
- TC-UC-012 / UC-LMS-004 Exception E1: Unauthorized user denied access to course materials
"""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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


def _setup_materials_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Algorithms & Data Structures",
        syllabus="Syllabus content",
        schedule_info="MWF 11:00",
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
    # Observer O1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=401,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_uc_007_faculty_adds_and_publishes_material(stub_iam):
    """Test ID: TC-UC-007.

    Source ID: UC-LMS-003 Main Flow
    Purpose: Verify that assigned Faculty can add a course material item to a
    module or weekly section and publish it immediately.
    """
    _setup_materials_world(101)
    client = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    pdf_file = SimpleUploadedFile(
        "module1_lecture.pdf",
        b"%PDF-1.4 sample lecture notes",
        content_type="application/pdf",
    )

    resp = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Module 1 Slides",
            "description": "Lecture 1 introduction slides",
            "material_type": MaterialType.FILE,
            "section_name": "Module 1",
            "sort_order": 1,
            "file_attachment": pdf_file,
        },
        format="multipart",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Module 1 Slides"
    assert data["section_name"] == "Module 1"
    assert data["status"] == MaterialStatus.PUBLISHED
    assert data["material_type"] == MaterialType.FILE

    # Verify immediately available in the course workspace
    mat = CourseMaterial.objects.get(id=data["id"])
    assert mat.status == MaterialStatus.PUBLISHED
    assert mat.course_id == 101


def test_tc_uc_008_faculty_edits_and_reorganizes_material(stub_iam):
    """Test ID: TC-UC-008.

    Source ID: UC-LMS-003 Alternative A1
    Purpose: Verify that assigned Faculty can edit and reorganize existing course materials.
    """
    _setup_materials_world(101)
    client = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    mat = CourseMaterial.objects.create(
        course_id=101,
        title="M1 Initial Title",
        material_type=MaterialType.NOTE,
        content_text="Introductory text",
        section_name="Module 1",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=101,
    )

    resp = client.patch(
        f"/api/v1/lms/materials/{mat.id}/",
        data={
            "title": "M1 Reorganized Title",
            "section_name": "Module 2",
        },
        format="json",
    )
    assert resp.status_code == 200
    updated_data = resp.json()
    assert updated_data["title"] == "M1 Reorganized Title"
    assert updated_data["section_name"] == "Module 2"

    mat.refresh_from_db()
    assert mat.title == "M1 Reorganized Title"
    assert mat.section_name == "Module 2"


def test_tc_uc_009_non_faculty_material_write_rejected(stub_iam):
    """Test ID: TC-UC-009.

    Source ID: UC-LMS-003 Exception E1
    Purpose: Verify that course material write attempts by non-Faculty roles
    (TA, Observer, or Student) are rejected.
    """
    _setup_materials_world(101)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Protected Material",
        material_type=MaterialType.NOTE,
        content_text="Protected Content",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=101,
    )

    non_faculty_users = [
        (201, _TA, "student", "teaching_assistant"),
        (301, _STUDENT, "student", "student"),
        (401, _OBSERVER, "student", "course_observer"),
    ]

    for uid, perms, kind, role in non_faculty_users:
        client = _make_client(stub_iam, user_id=uid, perms=perms, kind=kind, role=role)

        # 1. Attempt upload
        resp_upload = client.post(
            "/api/v1/lms/materials/",
            data={
                "course_id": 101,
                "title": f"Upload by {role}",
                "material_type": MaterialType.NOTE,
                "content_text": "Unauthorized text",
            },
            format="json",
        )
        assert resp_upload.status_code == 403

        # 2. Attempt edit
        resp_edit = client.patch(
            f"/api/v1/lms/materials/{mat.id}/",
            data={"title": f"Hacked by {role}"},
            format="json",
        )
        assert resp_edit.status_code == 403

        # 3. Attempt delete
        resp_del = client.delete(f"/api/v1/lms/materials/{mat.id}/")
        assert resp_del.status_code == 403

    # Preserves existing materials unchanged
    mat.refresh_from_db()
    assert mat.title == "Protected Material"
    assert CourseMaterial.objects.filter(course_id=101).count() == 1


def test_tc_uc_010_authorized_course_user_views_published_materials(stub_iam):
    """Test ID: TC-UC-010.

    Source ID: UC-LMS-004 Main Flow
    Purpose: Verify that an authorized course user can view published course
    materials in read-only form.
    """
    _setup_materials_world(101)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Published Reading 1",
        description="Required reading",
        material_type=MaterialType.NOTE,
        content_text="Read chapters 1 and 2",
        section_name="Week 1",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=101,
    )

    authorized_roles = [
        (301, _STUDENT, "student", "student"),
        (201, _TA, "student", "teaching_assistant"),
        (401, _OBSERVER, "student", "course_observer"),
    ]

    for uid, perms, kind, role in authorized_roles:
        client = _make_client(stub_iam, user_id=uid, perms=perms, kind=kind, role=role)

        # List published materials
        resp_list = client.get("/api/v1/lms/materials/?course_id=101")
        assert resp_list.status_code == 200
        items = resp_list.json()
        assert any(item["id"] == mat.id for item in items)

        # Retrieve material detail
        resp_detail = client.get(f"/api/v1/lms/materials/{mat.id}/")
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["id"] == mat.id
        assert detail["title"] == "Published Reading 1"
        assert detail["content_text"] == "Read chapters 1 and 2"


def test_tc_uc_011_scheduled_materials_omitted_from_students(stub_iam):
    """Test ID: TC-UC-011.

    Source ID: UC-LMS-004 Alternative A1
    Purpose: Verify that scheduled or unpublished materials are omitted from
    the materials view until released.
    """
    _setup_materials_world(101)
    now = timezone.now()

    # Published material
    mat_pub = CourseMaterial.objects.create(
        course_id=101,
        title="Available Material",
        material_type=MaterialType.NOTE,
        content_text="Immediately available",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=101,
    )
    # Scheduled material with future release date
    mat_sched = CourseMaterial.objects.create(
        course_id=101,
        title="Future Scheduled Material",
        material_type=MaterialType.NOTE,
        content_text="Should be hidden",
        status=MaterialStatus.SCHEDULED,
        release_date=now + timedelta(days=7),
        uploaded_by=101,
    )

    client_student = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Student listing materials
    resp = client_student.get("/api/v1/lms/materials/?course_id=101")
    assert resp.status_code == 200
    material_ids = [m["id"] for m in resp.json()]
    assert mat_pub.id in material_ids
    assert mat_sched.id not in material_ids

    # Student directly requesting scheduled material detail
    resp_direct = client_student.get(f"/api/v1/lms/materials/{mat_sched.id}/")
    assert resp_direct.status_code == 404


def test_tc_uc_012_unauthorized_user_denied_course_materials(stub_iam):
    """Test ID: TC-UC-012.

    Source ID: UC-LMS-004 Exception E1
    Purpose: Verify that access to course materials is denied to an unauthorized
    user not linked to the course.
    """
    _setup_materials_world(101)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Restricted Syllabus Material",
        material_type=MaterialType.NOTE,
        content_text="Secret notes",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=101,
    )

    # User U_unauth (user_id 777) has student perms but no membership in Course 101
    client_unauth = _make_client(
        stub_iam, user_id=777, perms=_STUDENT, kind="student", role="student"
    )

    # List materials for Course 101
    resp_list = client_unauth.get("/api/v1/lms/materials/?course_id=101")
    assert resp_list.status_code == 200
    assert resp_list.json() == []

    # Direct detail access
    resp_detail = client_unauth.get(f"/api/v1/lms/materials/{mat.id}/")
    assert resp_detail.status_code == 404
