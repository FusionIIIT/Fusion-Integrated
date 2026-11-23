"""Basis Workflow BW-LMS-04: Faculty Grading and Grade Release.

Covers:
- TC-WF-015 / BW-LMS-04 step-1-success: Submission -> Grade Draft by Faculty
- TC-WF-016 / BW-LMS-04 step-2-success: Grade Draft -> Released / Student Visible by Faculty
- TC-WF-017 / BW-LMS-04 full-path: End-to-end faculty grading and release lifecycle
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
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Algorithms",
        syllabus="Graph algorithms, DP, Complexity",
        schedule_info="TR 10:00",
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

    asg = Assignment.objects.create(
        course_id=course_id,
        title="Dynamic Programming Lab",
        instructions="Implement DP algorithm",
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
        content_text="def solve_knapsack(): pass",
        attempt_number=1,
    )

    return {
        "workspace": ws,
        "assignment": asg,
        "submission": sub,
    }


def test_tc_wf_015_step_1_faculty_grades_submission_to_draft(stub_iam):
    """Test ID: TC-WF-015.

    Source ID: BW-LMS-04 step-1-success
    Purpose: Verify transition from Student Submission Recorded to Grade Draft
    when assigned Faculty grades submission with points and feedback.
    """
    world = _setup_world(101)
    sub = world["submission"]

    # Precondition: Submission exists in Recorded state; no grade yet
    assert not SubmissionGrade.objects.filter(submission=sub).exists()

    # Action: Faculty F1 grades the submission
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp = client_fac.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "92.00",
            "feedback_text": "Optimal recurrence relation and clear complexity analysis.",
        },
        format="json",
    )
    assert resp.status_code == 200
    grade_data = resp.json()
    assert Decimal(str(grade_data["points_awarded"])) == Decimal("92.00")
    assert grade_data["feedback_text"] == "Optimal recurrence relation and clear complexity analysis."
    assert grade_data["status"] == GradeStatus.DRAFT
    assert grade_data["graded_by"] == 101

    # Verify Grade Draft stored in DB
    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.status == GradeStatus.DRAFT
    assert grade.points_awarded == Decimal("92.00")
    assert grade.graded_by == 101

    # Expected Result: Withheld from student view
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_student.status_code == 404


def test_tc_wf_016_step_2_faculty_releases_grade_draft(stub_iam):
    """Test ID: TC-WF-016.

    Source ID: BW-LMS-04 step-2-success
    Purpose: Verify transition from Grade Draft to Grade Released / Student Visible
    when assigned Faculty releases grade and feedback.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    # Precondition: Draft grade exists for Student S1 submission
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("95.00"),
        feedback_text="Excellent submission.",
        status=GradeStatus.DRAFT,
        graded_by=101,
    )

    # Student cannot view grade yet
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_before = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_before.status_code == 404

    # Action: Faculty F1 releases grades and feedback for Assignment A1
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_release = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp_release.status_code == 200
    assert resp_release.json()["published_count"] >= 1

    # Expected Result: Grade transitions to PUBLISHED with faculty attribution
    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101
    assert grade.published_at is not None

    # Student S1 can view grade and feedback in read-only form
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_student.status_code == 200
    student_view = resp_student.json()
    assert Decimal(str(student_view["points_awarded"])) == Decimal("95.00")
    assert student_view["feedback_text"] == "Excellent submission."


def test_tc_wf_017_full_path_faculty_grading_lifecycle(stub_iam):
    """Test ID: TC-WF-017.

    Source ID: BW-LMS-04 full-path
    Purpose: Verify the complete end-to-end faculty grading and grade release basis
    workflow from recorded submission through Faculty grading to student visibility.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    # Initial state: Student Submission Recorded, no grade
    assert not SubmissionGrade.objects.filter(submission=sub).exists()
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_initial = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_initial.status_code == 404

    # Step 1: Faculty grades submission -> Grade Draft
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_grade = client_fac.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "88.50",
            "feedback_text": "Good structure, slight boundary issue.",
        },
        format="json",
    )
    assert resp_grade.status_code == 200
    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.status == GradeStatus.DRAFT
    assert grade.points_awarded == Decimal("88.50")
    assert grade.graded_by == 101

    # Verify grade withheld from student view in draft state
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_draft_view = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_draft_view.status_code == 404

    # Step 2: Faculty releases draft grade -> Grade Released / Student Visible
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_pub = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp_pub.status_code == 200
    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101

    # Verify student S1 can view released grade in read-only form
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_final_view = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_final_view.status_code == 200
    view_data = resp_final_view.json()
    assert Decimal(str(view_data["points_awarded"])) == Decimal("88.50")
    assert view_data["feedback_text"] == "Good structure, slight boundary issue."
