"""Composite Workflow CW-LMS-01: Integrated Assignment Lifecycle.

Covers:
- TC-WF-022 / CW-LMS-01 step-1-success: New -> Assignment Draft
- TC-WF-023 / CW-LMS-01 step-2-immediate-decision: Branch A: Draft -> Available (Immediate)
- TC-WF-024 / CW-LMS-01 step-3-scheduled-decision: Branch B: Draft -> Scheduled (Future)
- TC-WF-025 / CW-LMS-01 step-4-holding-guard: Guard holding assignment while T < release
- TC-WF-026 / CW-LMS-01 step-4-system-release: Background task releases assignment at T >= release
- TC-WF-027 / CW-LMS-01 step-5-student-submission: Convergence: Student submits on available assignment
- TC-WF-028 / CW-LMS-01 immediate-release-path: Full Path 1 (Creation -> Immediate Publish -> Available -> Submit)
- TC-WF-029 / CW-LMS-01 scheduled-release-path: Full Path 2 (Creation -> Scheduled -> Auto-Release -> Submit)
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
        title="Distributed Systems",
        syllabus="Consensus, Replication, Fault Tolerance",
        schedule_info="MWF 13:00",
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


def test_tc_wf_022_step_1_create_assignment_draft(stub_iam):
    """Test ID: TC-WF-022.

    Source ID: CW-LMS-01 step-1-success
    Purpose: Verify composite workflow initiation transition from No Assignment / New
    to Assignment Draft upon valid assignment creation by Faculty.
    """
    _setup_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    due_dt = now + timedelta(days=10)

    # Faculty creates draft assignment
    resp = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Raft Consensus Lab",
            "instructions": "Implement leader election and log replication",
            "points_possible": "100.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == AssignmentStatus.DRAFT
    assert data["created_by"] == 101

    asg = Assignment.objects.get(id=data["id"])
    assert asg.status == AssignmentStatus.DRAFT
    assert asg.course_id == 101


def test_tc_wf_023_step_2_immediate_decision_branch(stub_iam):
    """Test ID: TC-WF-023.

    Source ID: CW-LMS-01 step-2-immediate-decision
    Purpose: Verify composite publication decision branch A transitioning Assignment Draft
    directly to Assignment Available for Submission when immediate release condition is chosen.
    """
    _setup_world(101)
    now = timezone.now()

    # Precondition: Assignment in Draft state without release_date
    asg = Assignment.objects.create(
        course_id=101,
        title="Paxos Protocol",
        instructions="Implement basic Paxos",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    # Action: Faculty publishes with immediate release condition
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp = client_fac.post(f"/api/v1/lms/assignments/{asg.id}/publish/")
    assert resp.status_code == 200
    assert resp.json()["status"] == AssignmentStatus.PUBLISHED

    # Expected Result: Transitions directly to PUBLISHED (Available for Submission)
    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Verify student can access assignment immediately
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_stu = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_stu.status_code == 200


def test_tc_wf_024_step_3_scheduled_decision_branch(stub_iam):
    """Test ID: TC-WF-024.

    Source ID: CW-LMS-01 step-3-scheduled-decision
    Purpose: Verify composite publication decision branch B transitioning Assignment Draft
    to Assignment Published / Scheduled for Release when future release schedule is chosen.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=3)

    # Precondition: Assignment in Draft state with future release date
    asg = Assignment.objects.create(
        course_id=101,
        title="Byzantine Fault Tolerance",
        instructions="PBFT consensus protocol",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        release_date=future_release,
        due_date=now + timedelta(days=10),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    # Action: Faculty executes publish
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp = client_fac.post(f"/api/v1/lms/assignments/{asg.id}/publish/")
    assert resp.status_code == 200
    assert resp.json()["status"] == AssignmentStatus.SCHEDULED

    # Expected Result: Transitions to SCHEDULED state
    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.SCHEDULED

    # Verify hidden from students
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_stu = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_stu.status_code == 404


def test_tc_wf_025_step_4_holding_guard_scheduled_assignment(stub_iam):
    """Test ID: TC-WF-025.

    Source ID: CW-LMS-01 step-4-holding-guard
    Purpose: Verify that an assignment on the scheduled composite path remains in
    Assignment Published / Scheduled for Release while current time has not reached
    the release schedule.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=2)

    # Precondition: Assignment in SCHEDULED state with future release date
    asg = Assignment.objects.create(
        course_id=101,
        title="Gossip Protocols",
        instructions="Epidemic broadcast trees",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        release_date=future_release,
        due_date=future_release + timedelta(days=5),
        status=AssignmentStatus.SCHEDULED,
        created_by=101,
    )

    # Action: System background task runs at T < T_release
    res = process_scheduled_content_release()
    assert res["assignments_released"] == 0

    # Expected Result: Guard condition evaluates to false; remains SCHEDULED
    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.SCHEDULED

    # Action: Student attempts to access or submit at T < T_release
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_view = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_view.status_code == 404

    resp_sub = client_stu.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Early attempt",
        },
        format="json",
    )
    assert resp_sub.status_code == 403


def test_tc_wf_026_step_4_system_release_upon_reaching_time(stub_iam):
    """Test ID: TC-WF-026.

    Source ID: CW-LMS-01 step-4-system-release
    Purpose: Verify automatic transition from Assignment Published / Scheduled for Release
    to Assignment Available for Submission when release time is reached.
    """
    _setup_world(101)
    now = timezone.now()
    past_release = now - timedelta(minutes=5)

    # Precondition: Assignment in SCHEDULED state whose release time has arrived
    asg = Assignment.objects.create(
        course_id=101,
        title="Vector Clocks",
        instructions="Implement causality tracking",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        release_date=past_release,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.SCHEDULED,
        created_by=101,
    )

    # Action: System background task runs at T >= T_release
    res = process_scheduled_content_release()
    assert res["assignments_released"] >= 1

    # Expected Result: Transitions to PUBLISHED (Available for Submission)
    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Available to students
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_stu = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_stu.status_code == 200
    assert resp_stu.json()["title"] == "Vector Clocks"


def test_tc_wf_027_step_5_student_submission_convergence(stub_iam):
    """Test ID: TC-WF-027.

    Source ID: CW-LMS-01 step-5-student-submission
    Purpose: Verify composite workflow convergence transition from Assignment Available
    for Submission to Student Submission Recorded upon valid on-time student submission.
    """
    _setup_world(101)
    now = timezone.now()

    # Precondition: Assignment in PUBLISHED state, current time before due date
    asg = Assignment.objects.create(
        course_id=101,
        title="Distributed Key-Value Store",
        instructions="Build consistent hashed DHT",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    # Action: Student S1 submits work
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_sub = client_stu.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Chord DHT implementation with finger tables",
        },
        format="json",
    )
    assert resp_sub.status_code == 201
    data = resp_sub.json()
    assert data["student_id"] == 301

    # Expected Result: Transition to Student Submission Recorded
    sub = AssignmentSubmission.objects.get(id=data["id"])
    assert sub.student_id == 301
    assert sub.assignment_id == asg.id
    assert sub.content_text == "Chord DHT implementation with finger tables"


def test_tc_wf_028_immediate_release_path_complete(stub_iam):
    """Test ID: TC-WF-028.

    Source ID: CW-LMS-01 immediate-release-path
    Purpose: Verify the complete integrated composite workflow Path 1:
    creation -> immediate publication -> available for submission -> on-time student submission.
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
            "title": "Path 1: Consensus Engine",
            "instructions": "Implement multi-paxos log",
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

    # Step 2: Faculty publishes immediately (Branch A)
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg_id}/publish/")
    assert resp_pub.status_code == 200
    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Step 3: Assignment Available for Submission
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_view = client_stu.get(f"/api/v1/lms/assignments/{asg_id}/")
    assert resp_view.status_code == 200

    # Step 4: Student S1 submits valid on-time deliverable
    resp_sub = client_stu.post(
        f"/api/v1/lms/assignments/{asg_id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "Paxos consensus implementation ready",
        },
        format="json",
    )
    assert resp_sub.status_code == 201
    sub_id = resp_sub.json()["id"]

    # Sequential transition verified: Draft -> Published/Available -> Submission Recorded
    sub = AssignmentSubmission.objects.get(id=sub_id)
    assert sub.student_id == 301
    assert sub.assignment_id == asg_id


def test_tc_wf_029_scheduled_release_path_complete(stub_iam):
    """Test ID: TC-WF-029.

    Source ID: CW-LMS-01 scheduled-release-path
    Purpose: Verify the complete integrated composite workflow Path 2:
    creation -> scheduled release -> system time trigger -> available for submission -> on-time student submission.
    """
    _setup_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=2)
    due_dt = now + timedelta(days=10)

    # Step 1: Faculty creates assignment draft with future release schedule
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_create = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Path 2: Byzantine Agreement",
            "instructions": "Implement Byzantine generals problem",
            "points_possible": "100.00",
            "submission_type": SubmissionType.TEXT,
            "release_date": future_release.isoformat(),
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp_create.status_code == 201
    asg_id = resp_create.json()["id"]
    asg = Assignment.objects.get(id=asg_id)
    assert asg.status == AssignmentStatus.DRAFT

    # Step 2: Faculty publishes scheduled assignment (Branch B)
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg_id}/publish/")
    assert resp_pub.status_code == 200
    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.SCHEDULED

    # Step 3: Holding guard (student cannot view or submit while T < T_release)
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/assignments/{asg_id}/").status_code == 404

    # Step 4: System release trigger (T reaches release timestamp)
    asg.release_date = timezone.now() - timedelta(minutes=1)
    asg.save()
    process_scheduled_content_release()

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Step 5: Assignment now Available for Submission
    resp_view = client_stu.get(f"/api/v1/lms/assignments/{asg_id}/")
    assert resp_view.status_code == 200

    # Step 6: Student S1 submits on-time work (Convergence)
    resp_sub = client_stu.post(
        f"/api/v1/lms/assignments/{asg_id}/submissions/",
        data={
            "submission_type": SubmissionType.TEXT,
            "content_text": "BFT consensus engine complete",
        },
        format="json",
    )
    assert resp_sub.status_code == 201
    sub_id = resp_sub.json()["id"]

    sub = AssignmentSubmission.objects.get(id=sub_id)
    assert sub.student_id == 301
    assert sub.assignment_id == asg_id
