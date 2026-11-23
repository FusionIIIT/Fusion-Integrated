"""Specification use case tests for LMS Assignment Submissions.

Covers:
- TC-UC-027 / UC-LMS-010 Main Flow: Enrolled Student submits on-time assignment work
- TC-UC-028 / UC-LMS-010 Exception E1: Inconsistent submission type rejected
- TC-UC-029 / UC-LMS-011 Main Flow: Student views own submission history and status
- TC-UC-030 / UC-LMS-011 Alternative A1: Submission standing display (submitted, missing)
- TC-UC-031 / UC-LMS-011 Exception E1: Student denied access to another student's submission
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.calculations import compute_submission_status
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    MembershipStatus,
    SubmissionType,
)
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


def _setup_submissions_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Database Systems",
        syllabus="Transactions, Indexing, Query Optimization",
        schedule_info="MWF 15:00",
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
    # Student S2
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=302,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_uc_027_student_submits_ontime_work(stub_iam):
    """Test ID: TC-UC-027.

    Source ID: UC-LMS-010 Main Flow
    Purpose: Verify that an enrolled Student can submit on-time assignment work
    matching the configured submission type.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Lab 1: SQL Indexing",
        instructions="Implement B+ tree indexing",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    pdf_submission = SimpleUploadedFile(
        "btree_solution.pdf",
        b"%PDF-1.4 SQL Indexing Assignment Solution",
        content_type="application/pdf",
    )

    resp = client_s1.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.FILE,
            "file_attachment": pdf_submission,
        },
        format="multipart",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["student_id"] == 301
    assert data["submission_type"] == SubmissionType.FILE
    assert "submitted_at" in data
    assert data["submitted_at"] is not None
    assert data["attempt_number"] == 1

    # Recorded in DB
    sub = AssignmentSubmission.objects.get(id=data["id"])
    assert sub.student_id == 301
    assert sub.assignment_id == asg.id


def test_tc_uc_028_inconsistent_submission_type_rejected(stub_iam):
    """Test ID: TC-UC-028.

    Source ID: UC-LMS-010 Exception E1
    Purpose: Verify that a student submission with a type inconsistent with
    assignment configuration is rejected.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Strict File Assignment",
        instructions="Upload code archive file only",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Attempt to submit text instead of file
    resp_text = client_s1.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Plain text solution",
        },
        format="json",
    )
    assert resp_text.status_code == 400
    assert "submission type must match" in resp_text.json().get("error", {}).get("message", "").lower()

    # Attempt to submit link instead of file
    resp_link = client_s1.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.LINK,
            "content_link": "https://github.com/repo",
        },
        format="json",
    )
    assert resp_link.status_code == 400

    # Ensure no submission was created
    assert AssignmentSubmission.objects.filter(assignment=asg).count() == 0


def test_tc_uc_029_student_views_own_submission_history(stub_iam):
    """Test ID: TC-UC-029.

    Source ID: UC-LMS-011 Main Flow
    Purpose: Verify that an enrolled Student can view their own assignment
    submission history and status.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Project 1",
        instructions="Complete project",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub_s1 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="S1 Initial attempt",
        attempt_number=1,
    )

    # Another student's submission in same assignment
    AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=302,
        submission_type=SubmissionType.TEXT,
        content_text="S2 Submission",
        attempt_number=1,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert resp.status_code == 200
    submissions = resp.json()

    # Returns only S1's submissions
    assert len(submissions) == 1
    assert submissions[0]["id"] == sub_s1.id
    assert submissions[0]["student_id"] == 301
    assert submissions[0]["content_text"] == "S1 Initial attempt"


def test_tc_uc_030_submission_standing_submitted_and_missing(stub_iam):
    """Test ID: TC-UC-030.

    Source ID: UC-LMS-011 Alternative A1
    Purpose: Verify that the system displays appropriate submission status
    values including submitted, late, or missing where applicable.
    """
    _setup_submissions_world(101)
    now = timezone.now()

    # Assignment A1: submitted on time
    asg1 = Assignment.objects.create(
        course_id=101,
        title="Assignment 1",
        instructions="Instructions A1",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )
    AssignmentSubmission.objects.create(
        assignment=asg1,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="S1 Completed A1",
    )

    # Assignment A2: unsubmitted overdue
    asg2 = Assignment.objects.create(
        course_id=101,
        title="Assignment 2",
        instructions="Instructions A2",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now - timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    # Domain calculation verification
    status_a1 = compute_submission_status(has_submitted=True, due_date=asg1.due_date, now=now)
    assert status_a1 == "SUBMITTED"

    status_a2 = compute_submission_status(has_submitted=False, due_date=asg2.due_date, now=now)
    assert status_a2 == "MISSING"

    # API verification
    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp_a1 = client_s1.get(f"/api/v1/lms/assignments/{asg1.id}/submissions/")
    assert resp_a1.status_code == 200
    assert len(resp_a1.json()) == 1

    resp_a2 = client_s1.get(f"/api/v1/lms/assignments/{asg2.id}/submissions/")
    assert resp_a2.status_code == 200
    assert len(resp_a2.json()) == 0


def test_tc_uc_031_student_denied_access_to_other_student_submission(stub_iam):
    """Test ID: TC-UC-031.

    Source ID: UC-LMS-011 Exception E1
    Purpose: Verify that a student is denied access to view another student's submission data.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Assignment 1",
        instructions="Instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub_s1 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="S1 Secret Solution",
    )

    client_s2 = _make_client(
        stub_iam, user_id=302, perms=_STUDENT, kind="student", role="student"
    )

    # S2 attempts direct GET on S1's submission
    resp_direct = client_s2.get(f"/api/v1/lms/submissions/{sub_s1.id}/")
    assert resp_direct.status_code == 404

    # S2 list submissions for assignment only sees own submissions (which is 0)
    resp_list = client_s2.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert resp_list.status_code == 200
    assert not any(s["id"] == sub_s1.id for s in resp_list.json())
