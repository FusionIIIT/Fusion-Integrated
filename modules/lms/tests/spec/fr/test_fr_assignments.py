"""Specification tests for LMS Course Assignments functional requirements.

Covers:
- TC-FR-017 / AFR-LMS-006.1: Create assignment (CFR-LMS-006)
- TC-FR-018 / AFR-LMS-006.2: Capture assignment configuration (CFR-LMS-006)
- TC-FR-019 / AFR-LMS-006.3: Edit assignment (CFR-LMS-006)
- TC-FR-020 / AFR-LMS-006.4: Maintain draft before publication (CFR-LMS-006)
- TC-FR-021 / AFR-LMS-007.1: Publish assignment (CFR-LMS-007)
- TC-FR-022 / AFR-LMS-007.2: Apply release-date visibility (CFR-LMS-007)
- TC-FR-023 / AFR-LMS-007.3: Release scheduled assignment (CFR-LMS-007)
- TC-FR-024 / AFR-LMS-007.4: View/download released assignment (CFR-LMS-007)
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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


def _setup_course(course_id: int = 101):
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
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_fr_017_create_assignment(stub_iam):
    """Test ID: TC-FR-017.

    Source ID: AFR-LMS-006.1: Create assignment (CFR-LMS-006)
    Purpose: Verify that Faculty can create a new assignment for an assigned course.
    """
    _setup_course(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    due = timezone.now() + timedelta(days=7)
    resp = client.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Programming Lab 1",
            "instructions": "Implement quicksort in Python.",
            "points_possible": "100.00",
            "submission_type": SubmissionType.FILE,
            "due_date": due.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Programming Lab 1"

    # Verify database persistence
    asg = Assignment.objects.get(id=data["id"])
    assert asg.course_id == 101
    assert asg.title == "Programming Lab 1"
    assert asg.created_by == 2001


def test_tc_fr_018_capture_assignment_configuration(stub_iam):
    """Test ID: TC-FR-018.

    Source ID: AFR-LMS-006.2: Capture assignment configuration (CFR-LMS-006)
    Purpose: Verify that the system captures and validates due date, instructions,
    submission type, and points possible when configuring an assignment.
    """
    _setup_course(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    due_dt = timezone.now() + timedelta(days=10)
    resp = client.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Exercise 1",
            "instructions": "Solve exercises 1-5",
            "points_possible": "100.00",
            "submission_type": SubmissionType.FILE,
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    asg = Assignment.objects.get(id=data["id"])
    assert asg.instructions == "Solve exercises 1-5"
    assert asg.points_possible == Decimal("100.00")
    assert asg.submission_type == SubmissionType.FILE
    assert asg.due_date is not None


def test_tc_fr_019_edit_assignment(stub_iam):
    """Test ID: TC-FR-019.

    Source ID: AFR-LMS-006.3: Edit assignment (CFR-LMS-006)
    Purpose: Verify that Faculty can edit an existing assignment in an assigned course.
    """
    _setup_course(101)
    asg = Assignment.objects.create(
        course_id=101,
        title="Initial Assignment Title",
        instructions="Initial Instructions",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT,
        due_date=timezone.now() + timedelta(days=3),
        status=AssignmentStatus.DRAFT,
        created_by=2001,
    )

    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    updated_due = timezone.now() + timedelta(days=14)
    resp = client.patch(
        f"/api/v1/lms/assignments/{asg.id}/",
        data={
            "instructions": "Updated Instructions: Solve exercises 1 to 10.",
            "due_date": updated_due.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["instructions"] == "Updated Instructions: Solve exercises 1 to 10."

    asg.refresh_from_db()
    assert asg.instructions == "Updated Instructions: Solve exercises 1 to 10."


def test_tc_fr_020_maintain_draft_before_publication(stub_iam):
    """Test ID: TC-FR-020.

    Source ID: AFR-LMS-006.4: Maintain draft before publication (CFR-LMS-006)
    Purpose: Verify that the system maintains an assignment in Draft state until
    explicitly published, keeping it unavailable to students.
    """
    _setup_course(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    # Faculty creates assignment without publishing
    resp = client.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Draft Homework",
            "instructions": "Draft instructions",
            "points_possible": "20.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": (timezone.now() + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    asg_id = resp.json()["id"]

    asg = Assignment.objects.get(id=asg_id)
    assert asg.status == AssignmentStatus.DRAFT

    # Enrolled Student attempts to view assignment -> withheld / 404
    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    stu_detail_resp = stu_client.get(f"/api/v1/lms/assignments/{asg_id}/")
    assert stu_detail_resp.status_code == 404

    stu_list_resp = stu_client.get("/api/v1/lms/assignments/?course_id=101")
    assert stu_list_resp.status_code == 200
    assert not any(a["id"] == asg_id for a in stu_list_resp.json())


def test_tc_fr_021_publish_assignment(stub_iam):
    """Test ID: TC-FR-021.

    Source ID: AFR-LMS-007.1: Publish assignment (CFR-LMS-007)
    Purpose: Verify that Faculty can publish a draft assignment.
    """
    _setup_course(101)
    asg = Assignment.objects.create(
        course_id=101,
        title="Ready to Publish Asg",
        instructions="Work on project",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.DRAFT,
        created_by=2001,
    )

    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    resp = client.post(f"/api/v1/lms/assignments/{asg.id}/publish/", data={}, format="json")
    assert resp.status_code == 200
    assert resp.json()["status"] == AssignmentStatus.PUBLISHED

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED


def test_tc_fr_022_apply_release_date_visibility(stub_iam):
    """Test ID: TC-FR-022.

    Source ID: AFR-LMS-007.2: Apply release-date visibility (CFR-LMS-007)
    Purpose: Verify that an assignment published with a future release date
    is withheld from students until the release date arrives.
    """
    _setup_course(101)
    future_release = timezone.now() + timedelta(days=3)
    asg = Assignment.objects.create(
        course_id=101,
        title="Future Scheduled Assignment",
        instructions="Complete upcoming lab.",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT,
        release_date=future_release,
        due_date=future_release + timedelta(days=7),
        status=AssignmentStatus.SCHEDULED,
        created_by=2001,
    )

    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")

    # Hidden from student in course assignment list
    list_resp = stu_client.get("/api/v1/lms/assignments/?course_id=101")
    assert list_resp.status_code == 200
    assert not any(a["id"] == asg.id for a in list_resp.json())

    # Hidden from student on detail endpoint
    detail_resp = stu_client.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert detail_resp.status_code == 404


def test_tc_fr_023_release_scheduled_assignment(stub_iam):
    """Test ID: TC-FR-023.

    Source ID: AFR-LMS-007.3: Release scheduled assignment (CFR-LMS-007)
    Purpose: Verify that scheduled assignment becomes available and visible
    to students when release time arrives.
    """
    _setup_course(101)
    past_release = timezone.now() - timedelta(minutes=5)
    asg = Assignment.objects.create(
        course_id=101,
        title="Due Scheduled Assignment",
        instructions="Work begins now.",
        points_possible=Decimal("80.00"),
        submission_type=SubmissionType.TEXT,
        release_date=past_release,
        due_date=past_release + timedelta(days=5),
        status=AssignmentStatus.SCHEDULED,
        created_by=2001,
    )

    # Celery release sweep
    result = process_scheduled_content_release()
    assert result["assignments_released"] >= 1

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Student views assignment list -> now visible
    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    list_resp = stu_client.get("/api/v1/lms/assignments/?course_id=101")
    assert list_resp.status_code == 200
    assert any(a["id"] == asg.id for a in list_resp.json())


def test_tc_fr_024_view_download_released_assignment(stub_iam):
    """Test ID: TC-FR-024.

    Source ID: AFR-LMS-007.4: View/download released assignment (CFR-LMS-007)
    Purpose: Verify that a registered Student can view assignment instructions
    and download associated assignment materials once released.
    """
    _setup_course(101)
    asg = Assignment.objects.create(
        course_id=101,
        title="Released Assignment With Materials",
        instructions="Refer to the attached handout for specifications.",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=timezone.now() + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )
    # Associated course material file
    handout_file = SimpleUploadedFile("handout.pdf", b"%PDF-1.4 Assignment Handout")
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Assignment Handout PDF",
        material_type=MaterialType.FILE,
        file_attachment=handout_file,
        status=MaterialStatus.PUBLISHED,
        uploaded_by=2001,
    )

    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")

    # 1. Student opens assignment and views instructions
    asg_resp = stu_client.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert asg_resp.status_code == 200
    asg_data = asg_resp.json()
    assert asg_data["title"] == "Released Assignment With Materials"
    assert asg_data["instructions"] == "Refer to the attached handout for specifications."

    # 2. Student downloads associated assignment material file
    dl_resp = stu_client.get(f"/api/v1/lms/materials/{mat.id}/download/")
    assert dl_resp.status_code == 200
    assert "attachment" in dl_resp.headers.get("Content-Disposition", "")

    # Cleanup material file
    mat.file_attachment.delete(save=False)
