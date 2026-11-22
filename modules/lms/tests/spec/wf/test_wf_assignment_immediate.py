"""Basis Workflow BW-LMS-02: Immediate Assignment Lifecycle.

Covers:
- TC-WF-005 / BW-LMS-02 step-1-success: Create assignment in Draft state
- TC-WF-006 / BW-LMS-02 step-2-success: Publish draft assignment immediately
- TC-WF-007 / BW-LMS-02 step-3-success: Student submits on-time deliverable
- TC-WF-008 / BW-LMS-02 full-path: End-to-end immediate assignment lifecycle
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
from modules.lms.registry import _FACULTY, _STUDENT

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
        title="Computer Architecture",
        syllabus="Syllabus",
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


def test_tc_wf_005_step_1_create_assignment_draft(stub_iam):
    """Test ID: TC-WF-005.

    Source ID: BW-LMS-02 step-1-success
    Purpose: Verify transition from No Assignment / New to Assignment Draft
    when Faculty configures valid assignment parameters.
    """
    _setup_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    due_dt = now + timedelta(days=10)

    resp = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Pipeline Hazard Lab",
            "instructions": "Implement forwarding unit",
            "points_possible": "100.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == AssignmentStatus.DRAFT
    asg = Assignment.objects.get(id=data["id"])
    assert asg.status == AssignmentStatus.DRAFT

    # Hidden from student
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_stu = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_stu.status_code == 404


def test_tc_wf_006_step_2_publish_assignment_immediately(stub_iam):
    """Test ID: TC-WF-006.

    Source ID: BW-LMS-02 step-2-success
    Purpose: Verify transition from Assignment Draft to Assignment Available
    for Submission when Faculty publishes with immediate release condition.
    """
    _setup_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Cache Simulation",
        instructions="Simulate 2-way set associative cache",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg.id}/publish/")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == AssignmentStatus.PUBLISHED

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Available to students for submission
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_stu = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_stu.status_code == 200
    assert resp_stu.json()["title"] == "Cache Simulation"


def test_tc_wf_007_step_3_student_submits_deliverable(stub_iam):
    """Test ID: TC-WF-007.

    Source ID: BW-LMS-02 step-3-success
    Purpose: Verify transition from Assignment Available for Submission to
    Student Submission Recorded when an enrolled student submits valid work before the due date.
    """
    _setup_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Branch Predictor",
        instructions="Implement 2-bit saturating counter",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_stu.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "2-bit branch predictor code solution",
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["student_id"] == 301
    assert "submitted_at" in data

    sub = AssignmentSubmission.objects.get(id=data["id"])
    assert sub.student_id == 301
    assert sub.assignment_id == asg.id


def test_tc_wf_008_full_path_immediate_assignment_lifecycle(stub_iam):
    """Test ID: TC-WF-008.

    Source ID: BW-LMS-02 full-path
    Purpose: Verify the complete end-to-end basis workflow from Faculty authoring
    through immediate publication and on-time Student submission.
    """
    _setup_world(101)
    now = timezone.now()
    due_dt = now + timedelta(days=7)

    # Step 1: Faculty creates assignment draft
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_create = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Full Path Architecture Lab",
            "instructions": "Complete pipeline benchmarks",
            "points_possible": "100.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp_create.status_code == 201
    asg_id = resp_create.json()["id"]

    asg = Assignment.objects.get(id=asg_id)
    assert asg.status == AssignmentStatus.DRAFT

    # Step 2: Faculty publishes immediately
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg_id}/publish/")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == AssignmentStatus.PUBLISHED

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Step 3: Student submits on-time deliverable
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_sub = client_stu.post(
        f"/api/v1/lms/assignments/{asg_id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Completed benchmark results and code",
        },
        format="json",
    )
    assert resp_sub.status_code == 201
    sub_id = resp_sub.json()["id"]

    sub = AssignmentSubmission.objects.get(id=sub_id)
    assert sub.student_id == 301
    assert sub.assignment_id == asg_id
