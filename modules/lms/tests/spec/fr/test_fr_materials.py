"""Specification tests for LMS Course Materials functional requirements.

Covers:
- TC-FR-006 / AFR-LMS-003.1: Upload supported material types (CFR-LMS-003)
- TC-FR-007 / AFR-LMS-003.2: Organize materials (CFR-LMS-003)
- TC-FR-008 / AFR-LMS-003.3: Schedule future material release (CFR-LMS-003)
- TC-FR-009 / AFR-LMS-003.4: Release scheduled material (CFR-LMS-003)
- TC-FR-010 / AFR-LMS-004.1: Student read-only material access (CFR-LMS-004)
- TC-FR-011 / AFR-LMS-004.2: TA read-only material access (CFR-LMS-004)
- TC-FR-012 / AFR-LMS-004.3: Observer read-only material access (CFR-LMS-004)
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


def _setup_course_with_members(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"C{course_id}",
        title="Intro to Computing",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=3001,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=4001,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_fr_006_upload_supported_material_types(stub_iam):
    """Test ID: TC-FR-006.

    Source ID: AFR-LMS-003.1: Upload supported material types (CFR-LMS-003)
    Purpose: Verify that Faculty can add course materials as files, external links,
    and text notes.
    """
    _setup_course_with_members(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    # 1. File Upload
    pdf_content = b"%PDF-1.4 Mock PDF Content"
    uploaded_file = SimpleUploadedFile(
        "document.pdf", pdf_content, content_type="application/pdf"
    )
    resp_file = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "document.pdf",
            "material_type": MaterialType.FILE,
            "file_attachment": uploaded_file,
            "section_name": "Readings",
        },
        format="multipart",
    )
    assert resp_file.status_code == 201
    file_mat_id = resp_file.json()["id"]

    # 2. Web Link
    resp_link = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Reference Documentation",
            "material_type": MaterialType.LINK,
            "external_url": "https://example.com/ref",
            "section_name": "Links",
        },
        format="json",
    )
    assert resp_link.status_code == 201
    link_mat_id = resp_link.json()["id"]

    # 3. Text Note
    resp_note = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Lecture Summary",
            "material_type": MaterialType.NOTE,
            "content_text": "Key takeaways from Lecture 1.",
            "section_name": "Notes",
        },
        format="json",
    )
    assert resp_note.status_code == 201
    note_mat_id = resp_note.json()["id"]

    # Verify all 3 saved in database with respective types
    file_mat = CourseMaterial.objects.get(id=file_mat_id)
    assert file_mat.material_type == MaterialType.FILE
    assert file_mat.file_attachment.name != ""
    # Clean up file on disk
    file_mat.file_attachment.delete(save=False)

    link_mat = CourseMaterial.objects.get(id=link_mat_id)
    assert link_mat.material_type == MaterialType.LINK
    assert link_mat.external_url == "https://example.com/ref"

    note_mat = CourseMaterial.objects.get(id=note_mat_id)
    assert note_mat.material_type == MaterialType.NOTE
    assert note_mat.content_text == "Key takeaways from Lecture 1."


def test_tc_fr_007_organize_materials(stub_iam):
    """Test ID: TC-FR-007.

    Source ID: AFR-LMS-003.2: Organize materials (CFR-LMS-003)
    Purpose: Verify that Faculty can organize course materials into modules
    or weekly sections.
    """
    _setup_course_with_members(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    resp = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Syllabus Handout",
            "material_type": MaterialType.NOTE,
            "content_text": "Overview of course modules.",
            "section_name": "Week 1 - Introduction",
            "sort_order": 1,
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["section_name"] == "Week 1 - Introduction"

    # Verify database organization
    mat = CourseMaterial.objects.get(id=data["id"])
    assert mat.section_name == "Week 1 - Introduction"


def test_tc_fr_008_schedule_future_material_release(stub_iam):
    """Test ID: TC-FR-008.

    Source ID: AFR-LMS-003.3: Schedule future material release (CFR-LMS-003)
    Purpose: Verify that Faculty can configure a future release date and time
    for course material.
    """
    _setup_course_with_members(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    future_release = timezone.now() + timedelta(days=5)
    resp = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Exam Prep Material",
            "material_type": MaterialType.NOTE,
            "content_text": "Review notes for Midterm.",
            "release_date": future_release.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == MaterialStatus.SCHEDULED
    mat = CourseMaterial.objects.get(id=data["id"])
    assert mat.status == MaterialStatus.SCHEDULED
    assert mat.release_date is not None


def test_tc_fr_009_release_scheduled_material(stub_iam):
    """Test ID: TC-FR-009.

    Source ID: AFR-LMS-003.4: Release scheduled material (CFR-LMS-003)
    Purpose: Verify that scheduled course material becomes published and available
    to authorized course users when the scheduled release time is reached.
    """
    _setup_course_with_members(101)
    past_release = timezone.now() - timedelta(minutes=5)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Scheduled Chapter Notes",
        material_type=MaterialType.NOTE,
        content_text="Now available chapter notes.",
        status=MaterialStatus.SCHEDULED,
        release_date=past_release,
        uploaded_by=2001,
    )

    # Sweep background release task
    result = process_scheduled_content_release()
    assert result["materials_released"] >= 1

    mat.refresh_from_db()
    assert mat.status == MaterialStatus.PUBLISHED

    # Enrolled Student accesses materials list
    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    resp = stu_client.get("/api/v1/lms/materials/?course_id=101")
    assert resp.status_code == 200
    material_ids = [m["id"] for m in resp.json()]
    assert mat.id in material_ids


def test_tc_fr_010_student_read_only_material_access(stub_iam):
    """Test ID: TC-FR-010.

    Source ID: AFR-LMS-004.1: Student read-only material access (CFR-LMS-004)
    Purpose: Verify that an enrolled Student can view published course materials
    in read-only form without edit or upload capabilities.
    """
    _setup_course_with_members(101)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Published Lecture 1 Slides",
        material_type=MaterialType.NOTE,
        content_text="Lecture 1 overview.",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=2001,
    )

    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")

    # Read access is permitted
    resp = stu_client.get("/api/v1/lms/materials/?course_id=101")
    assert resp.status_code == 200
    assert any(m["id"] == mat.id for m in resp.json())

    # Write / author actions are refused
    post_resp = stu_client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Student Upload Attempt",
            "material_type": MaterialType.NOTE,
            "content_text": "Forbidden",
        },
        format="json",
    )
    assert post_resp.status_code == 403

    patch_resp = stu_client.patch(
        f"/api/v1/lms/materials/{mat.id}/",
        data={"title": "Hacked Title"},
        format="json",
    )
    assert patch_resp.status_code == 403


def test_tc_fr_011_ta_read_only_material_access(stub_iam):
    """Test ID: TC-FR-011.

    Source ID: AFR-LMS-004.2: TA read-only material access (CFR-LMS-004)
    Purpose: Verify that an assigned TA can view published course materials in
    read-only form without material authoring or modification controls.
    """
    _setup_course_with_members(101)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Published Reference Book",
        material_type=MaterialType.LINK,
        external_url="https://example.com/book",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=2001,
    )

    ta_client = _make_client(stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant")

    # Read access is permitted
    resp = ta_client.get("/api/v1/lms/materials/?course_id=101")
    assert resp.status_code == 200
    assert any(m["id"] == mat.id for m in resp.json())

    # Material authoring / upload is refused for TA
    post_resp = ta_client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "TA Material Upload",
            "material_type": MaterialType.NOTE,
            "content_text": "TA notes",
        },
        format="json",
    )
    assert post_resp.status_code == 403


def test_tc_fr_012_observer_read_only_material_access(stub_iam):
    """Test ID: TC-FR-012.

    Source ID: AFR-LMS-004.3: Observer read-only material access (CFR-LMS-004)
    Purpose: Verify that a linked Observer can view published course materials
    in read-only form with no edit, upload, or modification capabilities.
    """
    _setup_course_with_members(101)
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Published Syllabus Outline",
        material_type=MaterialType.NOTE,
        content_text="Syllabus outline for observers.",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=2001,
    )

    obs_client = _make_client(stub_iam, user_id=4001, perms=_OBSERVER, kind="student", role="course_observer")

    # Read access is permitted
    resp = obs_client.get("/api/v1/lms/materials/?course_id=101")
    assert resp.status_code == 200
    assert any(m["id"] == mat.id for m in resp.json())

    # Write / upload operations are refused
    post_resp = obs_client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "Observer Upload Attempt",
            "material_type": MaterialType.NOTE,
            "content_text": "Should fail",
        },
        format="json",
    )
    assert post_resp.status_code == 403
