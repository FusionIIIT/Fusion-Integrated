"""Basis Workflow BW-LMS-05: TA Grading and Faculty Grade Release.

Covers:
- TC-WF-018 / BW-LMS-05 step-1-success: Submission -> Grade Draft by TA
- TC-WF-019 / BW-LMS-05 step-2-unauthorized-ta-release: Guard against TA releasing grades
- TC-WF-020 / BW-LMS-05 step-2-success: Faculty releases TA draft grade
- TC-WF-021 / BW-LMS-05 full-path: End-to-end TA grading and Faculty release lifecycle
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
        title="Operating Systems",
        syllabus="Virtual Memory, Concurrency, File Systems",
        schedule_info="MWF 14:00",
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

    asg = Assignment.objects.create(
        course_id=course_id,
        title="Virtual Memory Lab",
        instructions="Implement page replacement algorithm",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="LRU cache eviction policy implementation",
        attempt_number=1,
    )

    return {
        "workspace": ws,
        "assignment": asg,
        "submission": sub,
    }


def test_tc_wf_018_step_1_ta_grades_submission_to_draft(stub_iam):
    """Test ID: TC-WF-018.

    Source ID: BW-LMS-05 step-1-success
    Purpose: Verify transition from Student Submission Recorded to Grade Draft
    when an authorized TA grades a student submission with attribution.
    """
    world = _setup_world(101)
    sub = world["submission"]

    # Precondition: Recorded submission exists, no grade
    assert not SubmissionGrade.objects.filter(submission=sub).exists()

    # Action: TA T1 grades the submission
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp = client_ta.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "86.00",
            "feedback_text": "Good page replacement logic, clean edge case handling.",
        },
        format="json",
    )
    assert resp.status_code == 200
    grade_data = resp.json()
    assert Decimal(str(grade_data["points_awarded"])) == Decimal("86.00")
    assert grade_data["feedback_text"] == "Good page replacement logic, clean edge case handling."
    assert grade_data["status"] == GradeStatus.DRAFT
    assert grade_data["graded_by"] == 201

    # Verify Grade Draft in DB with TA attribution
    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.status == GradeStatus.DRAFT
    assert grade.points_awarded == Decimal("86.00")
    assert grade.graded_by == 201

    # Expected Result: Withheld from student view
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_student.status_code == 404


def test_tc_wf_019_step_2_unauthorized_ta_release_guard(stub_iam):
    """Test ID: TC-WF-019.

    Source ID: BW-LMS-05 step-2-unauthorized-ta-release
    Purpose: Verify that a TA is prohibited from releasing grades from Grade Draft
    to students and grade remains in draft state.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    # Precondition: Draft grade entered by TA exists
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("86.00"),
        feedback_text="Draft feedback by TA.",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    # Action: TA attempts to release grades
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp = client_ta.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    # Expected Result: Release action rejected (403 Forbidden)
    assert resp.status_code == 403

    # Evaluation remains in Grade Draft state
    grade.refresh_from_db()
    assert grade.status == GradeStatus.DRAFT
    assert grade.published_by is None
    assert grade.published_at is None

    # Grade remains hidden from student view
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_student.status_code == 404


def test_tc_wf_020_step_2_faculty_releases_ta_grade(stub_iam):
    """Test ID: TC-WF-020.

    Source ID: BW-LMS-05 step-2-success
    Purpose: Verify transition from Grade Draft to Grade Released / Student Visible
    when assigned Faculty releases grades previously drafted by a TA.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    # Precondition: TA-drafted evaluation exists
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("86.00"),
        feedback_text="TA graded feedback.",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    # Action: Faculty F1 reviews and releases grades
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

    # Expected Result: Transition to PUBLISHED with Faculty release attribution
    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101
    assert grade.published_at is not None
    # Original TA grader attribution is preserved
    assert grade.graded_by == 201

    # Enables Student S1 to view score and feedback
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_student.status_code == 200
    student_view = resp_student.json()
    assert Decimal(str(student_view["points_awarded"])) == Decimal("86.00")
    assert student_view["feedback_text"] == "TA graded feedback."


def test_tc_wf_021_full_path_ta_grading_and_faculty_release(stub_iam):
    """Test ID: TC-WF-021.

    Source ID: BW-LMS-05 full-path
    Purpose: Verify the complete end-to-end multi-actor basis workflow from recorded
    submission through TA grading and subsequent Faculty grade release.
    """
    world = _setup_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    # Initial state: Recorded submission, no grade
    assert not SubmissionGrade.objects.filter(submission=sub).exists()
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/").status_code == 404

    # Step 1: TA T1 grades submission -> Grade Draft
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )
    resp_grade = client_ta.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "89.00",
            "feedback_text": "Good implementation by TA.",
        },
        format="json",
    )
    assert resp_grade.status_code == 200
    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by == 201

    # Step 2 Guard: TA attempts release and is rejected
    resp_ta_pub = client_ta.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp_ta_pub.status_code == 403
    grade.refresh_from_db()
    assert grade.status == GradeStatus.DRAFT

    # Student cannot view draft grade
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/").status_code == 404

    # Step 3: Faculty F1 releases draft grade
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    resp_fac_pub = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp_fac_pub.status_code == 200

    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101
    assert grade.graded_by == 201

    # Step 4: Student S1 views released grade
    client_stu = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_view = client_stu.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_view.status_code == 200
    view_data = resp_view.json()
    assert Decimal(str(view_data["points_awarded"])) == Decimal("89.00")
    assert view_data["feedback_text"] == "Good implementation by TA."
