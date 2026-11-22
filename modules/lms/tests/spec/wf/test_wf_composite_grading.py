"""Composite Workflow CW-LMS-02: Integrated Grading and Grade Release Lifecycle.

Covers:
- TC-WF-030 / CW-LMS-02 step-1-faculty-grade: Branch A: Submission -> Grade Draft by Faculty
- TC-WF-031 / CW-LMS-02 step-2-ta-grade: Branch B: Submission -> Grade Draft by TA
- TC-WF-032 / CW-LMS-02 step-3-unauthorized-ta-release: Guard against TA releasing grades
- TC-WF-033 / CW-LMS-02 step-3-faculty-release: Faculty releases grade draft -> Student visible
- TC-WF-034 / CW-LMS-02 faculty-grading-path: Full Path 1 (Submission -> Faculty grades -> Faculty releases)
- TC-WF-035 / CW-LMS-02 ta-grading-path: Full Path 2 (Submission -> TA grades -> Faculty releases)
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
    GradeStatus,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseMembership,
    CourseWorkspace,
    SubmissionGrade,
)
from modules.lms.registry import _FACULTY, _STUDENT, _TA

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
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Database Systems",
        syllabus="Storage, Query Processing, Concurrency Control",
        schedule_info="TR 14:00",
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
        can_grade=True,
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

    asg = Assignment.objects.create(
        course_id=course_id,
        title="B-Tree Indexing Project",
        instructions="Implement B+ tree search and insertion",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub1 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="S1 B+ tree node splitting logic",
        attempt_number=1,
    )

    sub2 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=302,
        submission_type=SubmissionType.TEXT,
        content_text="S2 B+ tree leaf rebalancing logic",
        attempt_number=1,
    )

    return {
        "workspace": ws,
        "assignment": asg,
        "sub1": sub1,
        "sub2": sub2,
    }


def test_tc_wf_030_step_1_faculty_grades_submission(stub_iam):
    """Test ID: TC-WF-030.

    Source ID: CW-LMS-02 step-1-faculty-grade
    Purpose: Verify composite grading decision branch A transitioning Student
    Submission Recorded to Grade Draft when Faculty performs grading.
    """
    world = _setup_world(101)
    sub1 = world["sub1"]

    # Precondition: Student S1 submission in Recorded state, no grade
    assert not SubmissionGrade.objects.filter(submission=sub1).exists()

    # Action: Faculty F1 grades Student S1 submission (Branch A)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp = client_fac.post(
        f"/api/v1/lms/submissions/{sub1.id}/grade/",
        data={
            "points_awarded": "94.00",
            "feedback_text": "Excellent B+ tree splitting implementation.",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["points_awarded"])) == Decimal("94.00")
    assert data["status"] == GradeStatus.DRAFT
    assert data["graded_by"] == 101

    # Expected Result: Stored in Grade Draft state; withheld from student view
    grade = SubmissionGrade.objects.get(submission=sub1)
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by == 101

    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/submissions/{sub1.id}/grade-detail/").status_code == 404


def test_tc_wf_031_step_2_ta_grades_submission(stub_iam):
    """Test ID: TC-WF-031.

    Source ID: CW-LMS-02 step-2-ta-grade
    Purpose: Verify composite grading decision branch B transitioning Student
    Submission Recorded to Grade Draft when an authorized TA performs grading.
    """
    world = _setup_world(101)
    sub2 = world["sub2"]

    # Precondition: Student S2 submission in Recorded state, no grade
    assert not SubmissionGrade.objects.filter(submission=sub2).exists()

    # Action: TA T1 grades Student S2 submission (Branch B)
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp = client_ta.post(
        f"/api/v1/lms/submissions/{sub2.id}/grade/",
        data={
            "points_awarded": "87.00",
            "feedback_text": "Good rebalancing, check boundary conditions on root collapse.",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["points_awarded"])) == Decimal("87.00")
    assert data["status"] == GradeStatus.DRAFT
    assert data["graded_by"] == 201

    # Expected Result: Stored in Grade Draft state attributed to TA; withheld from student view
    grade = SubmissionGrade.objects.get(submission=sub2)
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by == 201

    client_stu2 = _make_client(
        stub_iam, user_id=302, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu2.get(f"/api/v1/lms/submissions/{sub2.id}/grade-detail/").status_code == 404


def test_tc_wf_032_step_3_unauthorized_ta_release_guard(stub_iam):
    """Test ID: TC-WF-032.

    Source ID: CW-LMS-02 step-3-unauthorized-ta-release
    Purpose: Verify composite grade release guard enforcement preventing TA from
    releasing grade drafts and maintaining evaluation in Grade Draft state.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub1 = world["sub1"]

    # Precondition: Grade draft exists
    grade = SubmissionGrade.objects.create(
        submission=sub1,
        points_awarded=Decimal("90.00"),
        feedback_text="Draft feedback",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    # Action: TA attempts grade release
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp = client_ta.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub1.id]},
        format="json",
    )
    # Expected Result: Rejection (403 Forbidden)
    assert resp.status_code == 403

    # Evaluation maintained in Grade Draft state
    grade.refresh_from_db()
    assert grade.status == GradeStatus.DRAFT
    assert grade.published_by is None

    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/submissions/{sub1.id}/grade-detail/").status_code == 404


def test_tc_wf_033_step_3_faculty_releases_grade_draft(stub_iam):
    """Test ID: TC-WF-033.

    Source ID: CW-LMS-02 step-3-faculty-release
    Purpose: Verify composite grade release transition from Grade Draft to
    Grade Released / Student Visible when assigned Faculty releases grades.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub1 = world["sub1"]

    # Precondition: Grade draft exists (created by TA or Faculty)
    grade = SubmissionGrade.objects.create(
        submission=sub1,
        points_awarded=Decimal("91.00"),
        feedback_text="Comprehensive tests and robust B+ tree operations.",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    # Action: Faculty F1 executes grade release
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub1.id]},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["published_count"] >= 1

    # Expected Result: Transition to Grade Released / Student Visible
    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101

    # Score and feedback readable by enrolled student
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_stu = client_stu.get(f"/api/v1/lms/submissions/{sub1.id}/grade-detail/")
    assert resp_stu.status_code == 200
    view_data = resp_stu.json()
    assert Decimal(str(view_data["points_awarded"])) == Decimal("91.00")
    assert view_data["feedback_text"] == "Comprehensive tests and robust B+ tree operations."


def test_tc_wf_034_faculty_grading_path_complete(stub_iam):
    """Test ID: TC-WF-034.

    Source ID: CW-LMS-02 faculty-grading-path
    Purpose: Verify the complete integrated composite grading workflow Path 1:
    recorded submission -> Faculty grading to draft -> Faculty release of grade to student.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub1 = world["sub1"]

    # Initial state: Recorded submission, no grade
    assert not SubmissionGrade.objects.filter(submission=sub1).exists()
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/submissions/{sub1.id}/grade-detail/").status_code == 404

    # Step 1: Faculty grades submission -> Grade Draft
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_grade = client_fac.post(
        f"/api/v1/lms/submissions/{sub1.id}/grade/",
        data={
            "points_awarded": "96.00",
            "feedback_text": "Path 1: Clean faculty grading.",
        },
        format="json",
    )
    assert resp_grade.status_code == 200
    grade = SubmissionGrade.objects.get(submission=sub1)
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by == 101

    # Verify withheld from student
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/submissions/{sub1.id}/grade-detail/").status_code == 404

    # Step 2: Faculty releases draft grade -> Grade Released / Student Visible
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_pub = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub1.id]},
        format="json",
    )
    assert resp_pub.status_code == 200

    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101

    # Student views grade
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_view = client_stu.get(f"/api/v1/lms/submissions/{sub1.id}/grade-detail/")
    assert resp_view.status_code == 200
    assert Decimal(str(resp_view.json()["points_awarded"])) == Decimal("96.00")
    assert resp_view.json()["feedback_text"] == "Path 1: Clean faculty grading."


def test_tc_wf_035_ta_grading_path_complete(stub_iam):
    """Test ID: TC-WF-035.

    Source ID: CW-LMS-02 ta-grading-path
    Purpose: Verify the complete integrated composite grading workflow Path 2:
    recorded submission -> TA grading to draft -> Faculty release of grade to student.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub2 = world["sub2"]

    # Initial state: Recorded submission, no grade
    assert not SubmissionGrade.objects.filter(submission=sub2).exists()
    client_stu2 = _make_client(
        stub_iam, user_id=302, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu2.get(f"/api/v1/lms/submissions/{sub2.id}/grade-detail/").status_code == 404

    # Step 1: TA grades submission -> Grade Draft
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp_grade = client_ta.post(
        f"/api/v1/lms/submissions/{sub2.id}/grade/",
        data={
            "points_awarded": "88.00",
            "feedback_text": "Path 2: TA evaluation of leaf rebalancing.",
        },
        format="json",
    )
    assert resp_grade.status_code == 200
    grade = SubmissionGrade.objects.get(submission=sub2)
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by == 201

    # Verify guard: TA cannot release
    resp_ta_pub = client_ta.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub2.id]},
        format="json",
    )
    assert resp_ta_pub.status_code == 403
    grade.refresh_from_db()
    assert grade.status == GradeStatus.DRAFT

    # Verify withheld from student
    client_stu2 = _make_client(
        stub_iam, user_id=302, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu2.get(f"/api/v1/lms/submissions/{sub2.id}/grade-detail/").status_code == 404

    # Step 2: Faculty reviews and releases TA draft grade -> Grade Released / Student Visible
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_fac_pub = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub2.id]},
        format="json",
    )
    assert resp_fac_pub.status_code == 200

    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101
    assert grade.graded_by == 201

    # Step 3: Student S2 views released grade
    client_stu2 = _make_client(
        stub_iam, user_id=302, perms=_STUDENT, kind="student", role="student"
    )
    resp_view = client_stu2.get(f"/api/v1/lms/submissions/{sub2.id}/grade-detail/")
    assert resp_view.status_code == 200
    assert Decimal(str(resp_view.json()["points_awarded"])) == Decimal("88.00")
    assert resp_view.json()["feedback_text"] == "Path 2: TA evaluation of leaf rebalancing."
