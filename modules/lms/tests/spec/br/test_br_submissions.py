"""Specification business rule tests for LMS Assignment Submissions.

Covers:
- TC-BR-025 / BR-LMS-012 permitted: Conforming submission accepted
- TC-BR-026 / BR-LMS-012 prohibited: Non-conforming submission rejected
- TC-BR-027 / BR-LMS-013 permitted: On-time submission accepted with timestamp
- TC-BR-028 / BR-LMS-013 prohibited: Late submission rejected under baseline on-time rule
- TC-BR-029 / BR-LMS-014 permitted: Student views own submission history
- TC-BR-030 / BR-LMS-014 prohibited: Student prohibited from viewing peer submissions
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
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
        title="Web Systems",
        syllabus="Protocols, Security, APIs",
        schedule_info="MWF 12:00",
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
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=302,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_br_025_conforming_submission_accepted(stub_iam):
    """Test ID: TC-BR-025.

    Source ID: BR-LMS-012 permitted
    Purpose: Verify that a Student submission conforming to the configured
    submission type is accepted.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="HTTP Server Lab",
        instructions="Implement simple HTTP 1.1 parser",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "HTTP/1.1 200 OK parser implementation",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["submission_type"] == SubmissionType.TEXT
    assert data["student_id"] == 301
    assert "submitted_at" in data


def test_tc_br_026_non_conforming_submission_rejected(stub_iam):
    """Test ID: TC-BR-026.

    Source ID: BR-LMS-012 prohibited
    Purpose: Verify that a Student submission failing to conform to the
    configured submission type is rejected.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="File Only Assignment",
        instructions="Upload source archive",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Non-conforming text submission",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert AssignmentSubmission.objects.filter(assignment=asg).count() == 0


def test_tc_br_027_ontime_submission_accepted_with_timestamp(stub_iam):
    """Test ID: TC-BR-027.

    Source ID: BR-LMS-013 permitted
    Purpose: Verify that the system accepts and records a Student submission
    made before the due date, recording the submission timestamp.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="On-time Lab",
        instructions="Complete tasks on time",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=3),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "On-time work submitted successfully",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert "submitted_at" in resp.json()
    assert resp.json()["submitted_at"] is not None


def test_tc_br_028_late_submission_rejected_under_baseline(stub_iam):
    """Test ID: TC-BR-028.

    Source ID: BR-LMS-013 prohibited
    Purpose: Verify that a submission attempted after the due date is not accepted
    under the baseline on-time rule, deferring late handling per ISS-LMS-001.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg_past_due = Assignment.objects.create(
        course_id=101,
        title="Expired Deadline Lab",
        instructions="Deadline is passed",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now - timedelta(hours=2),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Submitting past deadline raises ConflictError (409) under baseline
    resp = client_s1.post(
        f"/api/v1/lms/assignments/{asg_past_due.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Late attempt",
        },
        format="json",
    )
    assert resp.status_code == 409
    assert AssignmentSubmission.objects.filter(assignment=asg_past_due).count() == 0


def test_tc_br_029_student_views_own_submission_history(stub_iam):
    """Test ID: TC-BR-029.

    Source ID: BR-LMS-014 permitted
    Purpose: Verify that an enrolled Student is permitted to view their own
    submission history and status.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="History Lab",
        instructions="Instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="S1 Solution history",
        attempt_number=1,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert resp.status_code == 200
    submissions = resp.json()
    assert len(submissions) == 1
    assert submissions[0]["id"] == sub.id
    assert submissions[0]["student_id"] == 301
    assert submissions[0]["content_text"] == "S1 Solution history"


def test_tc_br_030_student_prohibited_from_viewing_peer_submission(stub_iam):
    """Test ID: TC-BR-030.

    Source ID: BR-LMS-014 prohibited
    Purpose: Verify that a Student is prohibited from viewing another student's
    submission history or status.
    """
    _setup_submissions_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Privacy Lab",
        instructions="Instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub_s2 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=302,
        submission_type=SubmissionType.TEXT,
        content_text="S2 Private work",
        attempt_number=1,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Direct access to S2's submission returns 404
    resp_detail = client_s1.get(f"/api/v1/lms/submissions/{sub_s2.id}/")
    assert resp_detail.status_code == 404

    # List submissions conceals S2's submissions
    resp_list = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert resp_list.status_code == 200
    assert not any(s["id"] == sub_s2.id for s in resp_list.json())
