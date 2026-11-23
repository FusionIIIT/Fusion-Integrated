"""Basis Workflow BW-LMS-03: Scheduled Assignment Lifecycle.

Covers:
- TC-WF-009 / BW-LMS-03 step-1-success: Create assignment draft for scheduled release
- TC-WF-010 / BW-LMS-03 step-2-success: Publish draft with future release date to Scheduled
- TC-WF-011 / BW-LMS-03 step-3-holding-guard: Assignment remains withheld prior to release
- TC-WF-012 / BW-LMS-03 step-3-success: Scheduled assignment transitions to Available at release time
- TC-WF-013 / BW-LMS-03 step-4-success: Student submits deliverable on released assignment
- TC-WF-014 / BW-LMS-03 full-path: End-to-end scheduled assignment release and submission
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
        title="Parallel Computing",
        syllabus="Syllabus",
        schedule_info="MWF 14:00",
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


def test_tc_wf_009_step_1_create_draft_for_scheduled_release(stub_iam):
    """Test ID: TC-WF-009.

    Source ID: BW-LMS-03 step-1-success
    Purpose: Verify transition from No Assignment / New to Assignment Draft when
    Faculty creates an assignment intended for scheduled release.
    """
    _setup_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    due_dt = now + timedelta(days=14)

    resp = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "CUDA Kernel Lab",
            "instructions": "Implement parallel matrix multiplication",
            "points_possible": "100.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    asg = Assignment.objects.get(id=resp.json()["id"])
    assert asg.status == AssignmentStatus.DRAFT


def test_tc_wf_010_step_2_publish_draft_with_future_schedule(stub_iam):
    """Test ID: TC-WF-010.

    Source ID: BW-LMS-03 step-2-success
    Purpose: Verify transition from Assignment Draft to Assignment Published /
    Scheduled for Release when Faculty publishes with future release configured.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=3)
    due_dt = now + timedelta(days=14)

    asg = Assignment.objects.create(
        course_id=101,
        title="MPI Cluster Lab",
        instructions="Implement ring-based allreduce",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        release_date=future_release,
        due_date=due_dt,
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg.id}/publish/")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == AssignmentStatus.SCHEDULED

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.SCHEDULED


def test_tc_wf_011_step_3_holding_guard_scheduled_assignment(stub_iam):
    """Test ID: TC-WF-011.

    Source ID: BW-LMS-03 step-3-holding-guard
    Purpose: Verify that an assignment in Assignment Published / Scheduled for
    Release remains in scheduled state and inaccessible to students while current
    time is before the release date.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=4)

    asg = Assignment.objects.create(
        course_id=101,
        title="OpenMP Lab",
        instructions="Parallel loops",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        release_date=future_release,
        due_date=future_release + timedelta(days=7),
        status=AssignmentStatus.SCHEDULED,
        created_by=101,
    )

    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # 1. Hidden from list
    resp_list = client_stu.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_list.status_code == 200
    assert asg.id not in [a["id"] for a in resp_list.json()]

    # 2. Detail returns 404
    assert client_stu.get(f"/api/v1/lms/assignments/{asg.id}/").status_code == 404

    # 3. Release task does not transition it early
    res = process_scheduled_content_release()
    assert res["assignments_released"] == 0

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.SCHEDULED


def test_tc_wf_012_step_3_success_scheduled_to_available(stub_iam):
    """Test ID: TC-WF-012.

    Source ID: BW-LMS-03 step-3-success
    Purpose: Verify transition from Assignment Published / Scheduled for Release
    to Assignment Available for Submission when configured release time is reached.
    """
    _setup_world(101)
    now = timezone.now()
    past_release = now - timedelta(minutes=5)

    asg = Assignment.objects.create(
        course_id=101,
        title="Vectorization Lab",
        instructions="SIMD vector intrinsics",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        release_date=past_release,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.SCHEDULED,
        created_by=101,
    )

    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Pre-task: inaccessible
    assert client_stu.get(f"/api/v1/lms/assignments/{asg.id}/").status_code == 404

    # Action: Task processes scheduled release
    res = process_scheduled_content_release()
    assert res["assignments_released"] >= 1

    # Transitioned to Available (PUBLISHED)
    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Post-task: accessible
    resp = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Vectorization Lab"


def test_tc_wf_013_step_4_student_submits_to_released_assignment(stub_iam):
    """Test ID: TC-WF-013.

    Source ID: BW-LMS-03 step-4-success
    Purpose: Verify transition from Assignment Available for Submission to
    Student Submission Recorded upon valid on-time student submission.
    """
    _setup_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="MapReduce Lab",
        instructions="Implement word count mapper and reducer",
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
            "content_text": "MapReduce mapper and reducer implementation",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert "submitted_at" in resp.json()

    sub = AssignmentSubmission.objects.get(id=resp.json()["id"])
    assert sub.student_id == 301
    assert sub.assignment_id == asg.id


def test_tc_wf_014_full_path_scheduled_assignment_workflow(stub_iam):
    """Test ID: TC-WF-014.

    Source ID: BW-LMS-03 full-path
    Purpose: Verify the complete end-to-end scheduled assignment release and
    submission basis workflow from creation through future release and on-time student submission.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=2)
    due_dt = now + timedelta(days=10)

    # Step 1: Faculty creates draft assignment with future release schedule
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_create = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Full Path Scheduled Assignment",
            "instructions": "Distributed consensus lab",
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

    # Step 2: Faculty publishes with future release
    asg.release_date = future_release
    asg.save(update_fields=["release_date"])

    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg_id}/publish/")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == AssignmentStatus.SCHEDULED

    # Step 3: Holding guard verifies student cannot access prior to release
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/assignments/{asg_id}/").status_code == 404

    # Step 4: Time arrives, automated release triggers
    asg.release_date = now - timedelta(minutes=1)
    asg.save(update_fields=["release_date"])

    res = process_scheduled_content_release()
    assert res["assignments_released"] >= 1

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Step 5: Student submits deliverable on released assignment
    resp_sub = client_stu.post(
        f"/api/v1/lms/assignments/{asg_id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Consensus algorithm complete submission",
        },
        format="json",
    )
    assert resp_sub.status_code == 201
    assert AssignmentSubmission.objects.filter(assignment=asg, student_id=301).exists()
