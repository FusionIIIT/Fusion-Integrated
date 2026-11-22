"""Specification tests for LMS Assignment Submissions functional requirements.

Covers:
- TC-FR-025 / AFR-LMS-008.1: Submit configured work type (CFR-LMS-008)
- TC-FR-026 / AFR-LMS-008.2: Accept on-time submission (CFR-LMS-008)
- TC-FR-027 / AFR-LMS-009.1: View own submission history (CFR-LMS-009)
- TC-FR-028 / AFR-LMS-009.2: View own submission status (CFR-LMS-009)
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.lms import selectors
from modules.lms.domain.calculations import compute_submission_status
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    MembershipStatus,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.domain.rules import is_submission_ontime
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseMembership,
    CourseWorkspace,
)
from modules.lms.registry import _STUDENT

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


def _setup_course_and_students(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"C{course_id}",
        title="Intro to Computing",
    )
    # Instructor
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # Student S1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Student S2
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=1002,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_fr_025_submit_configured_work_type(stub_iam):
    """Test ID: TC-FR-025.

    Source ID: AFR-LMS-008.1: Submit configured work type (CFR-LMS-008)
    Purpose: Verify that the system accepts student submissions conforming
    to the configured submission type (file, text, or link).
    """
    _setup_course_and_students(101)
    asg = Assignment.objects.create(
        course_id=101,
        title="File Submission Assignment",
        instructions="Submit your report in PDF.",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )

    client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    sub_file = SimpleUploadedFile("document.pdf", b"%PDF-1.4 Student Solution", content_type="application/pdf")

    resp = client.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.FILE,
            "file_attachment": sub_file,
        },
        format="multipart",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["submission_type"] == SubmissionType.FILE
    assert data["student_id"] == 1001

    # Verify submission record in database
    sub = AssignmentSubmission.objects.get(id=data["id"])
    assert sub.submission_type == SubmissionType.FILE
    assert sub.student_id == 1001
    assert sub.file_attachment.name != ""

    # Cleanup disk file
    sub.file_attachment.delete(save=False)


def test_tc_fr_026_accept_on_time_submission(stub_iam):
    """Test ID: TC-FR-026.

    Source ID: AFR-LMS-008.2: Accept on-time submission (CFR-LMS-008)
    Purpose: Verify that the system accepts and records on-time submissions
    submitted before the due date.
    """
    _setup_course_and_students(101)
    now = timezone.now()
    due_date = now + timedelta(days=3)
    asg = Assignment.objects.create(
        course_id=101,
        title="On-Time Essay Assignment",
        instructions="Write an essay.",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT,
        due_date=due_date,
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )

    client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    resp = client.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "This is an on-time essay submission.",
        },
        format="json",
    )
    assert resp.status_code == 201

    sub = AssignmentSubmission.objects.get(id=resp.json()["id"])
    assert sub.status == SubmissionStatus.SUBMITTED
    assert is_submission_ontime(sub.submitted_at, asg.due_date) is True


def test_tc_fr_027_view_own_submission_history(stub_iam):
    """Test ID: TC-FR-027.

    Source ID: AFR-LMS-009.1: View own submission history (CFR-LMS-009)
    Purpose: Verify that a Student can view only their own submission history
    and not the submissions of other students.
    """
    _setup_course_and_students(101)
    asg = Assignment.objects.create(
        course_id=101,
        title="Submission History Asg",
        instructions="Submit text notes.",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=timezone.now() + timedelta(days=4),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )
    # Student 1 submission
    sub1 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=1001,
        submission_type=SubmissionType.TEXT,
        content_text="Student 1 Work",
    )
    # Student 2 submission
    sub2 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=1002,
        submission_type=SubmissionType.TEXT,
        content_text="Student 2 Work",
    )

    # Student 1 accesses submissions list for the assignment
    client_s1 = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    resp_list = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert resp_list.status_code == 200
    submissions = resp_list.json()

    # Shows Student S1's own submission
    assert any(s["id"] == sub1.id for s in submissions)
    # Conceals other students' submissions
    assert not any(s["id"] == sub2.id for s in submissions)

    # Attempt to view Student 2's submission directly returns 404
    resp_s2_detail = client_s1.get(f"/api/v1/lms/submissions/{sub2.id}/")
    assert resp_s2_detail.status_code == 404


def test_tc_fr_028_view_own_submission_status(stub_iam):
    """Test ID: TC-FR-028.

    Source ID: AFR-LMS-009.2: View own submission status (CFR-LMS-009)
    Purpose: Verify that the system shows the Student's own submission status
    as submitted, late, or missing where applicable.
    """
    _setup_course_and_students(101)
    now = timezone.now()

    # Assignment A1: submitted on time
    asg1 = Assignment.objects.create(
        course_id=101,
        title="Assignment 1",
        instructions="Solve lab 1",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )
    AssignmentSubmission.objects.create(
        assignment=asg1,
        student_id=1001,
        submission_type=SubmissionType.TEXT,
        content_text="Completed on time",
    )

    # Assignment A2: unsubmitted and past due date
    asg2 = Assignment.objects.create(
        course_id=101,
        title="Assignment 2",
        instructions="Solve lab 2",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now - timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )

    # Validate dynamic standing computation via pure domain logic
    status_a1 = compute_submission_status(has_submitted=True, due_date=asg1.due_date, now=now)
    assert status_a1 == "SUBMITTED"

    status_a2 = compute_submission_status(has_submitted=False, due_date=asg2.due_date, now=now)
    assert status_a2 == "MISSING"

    # Validate student submission retrieval via selectors
    student_principal = make_principal(
        user_id=1001,
        kind="student",
        active_role="student",
        roles=("student",),
        modules=("lms",),
        permissions=_STUDENT,
    )
    sub1_record = selectors.get_student_submission(asg1.id, student_principal)
    assert sub1_record is not None
    assert sub1_record.status == SubmissionStatus.SUBMITTED

    sub2_record = selectors.get_student_submission(asg2.id, student_principal)
    assert sub2_record is None
