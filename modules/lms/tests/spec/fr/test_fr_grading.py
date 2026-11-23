"""Specification tests for LMS Grading and Grade Release functional requirements.

Covers:
- TC-FR-029 / AFR-LMS-010.1: Faculty grades submission (CFR-LMS-010)
- TC-FR-030 / AFR-LMS-010.2: TA grades submission (CFR-LMS-010)
- TC-FR-031 / AFR-LMS-010.3: Attribute grading action (CFR-LMS-010)
- TC-FR-032 / AFR-LMS-011.1: Hold grade in draft (CFR-LMS-011)
- TC-FR-033 / AFR-LMS-011.2: Hide draft grade from Student (CFR-LMS-011)
- TC-FR-034 / AFR-LMS-011.3: Faculty releases grade/feedback (CFR-LMS-011)
- TC-FR-035 / AFR-LMS-012.1: View own released grade/feedback (CFR-LMS-012)
- TC-FR-036 / AFR-LMS-012.2: Released grade is read-only to Student (CFR-LMS-012)
- TC-FR-037 / AFR-LMS-013.1: Log post-release grade change actor (CFR-LMS-013)
- TC-FR-038 / AFR-LMS-013.2: Log post-release grade change time (CFR-LMS-013)
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
    GradeChangeAudit,
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


def _setup_grading_env(course_id: int = 101):
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"C{course_id}",
        title="Intro to Computing",
    )
    # Faculty F1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=3001,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_grade=True,
    )
    # Student S1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    asg = Assignment.objects.create(
        course_id=course_id,
        title="Project Milestone 1",
        instructions="Complete milestone specifications.",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=timezone.now() + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=1001,
        submission_type=SubmissionType.TEXT,
        content_text="Milestone 1 completed solution.",
    )
    return asg, sub


def test_tc_fr_029_faculty_grades_submission(stub_iam):
    """Test ID: TC-FR-029.

    Source ID: AFR-LMS-010.1: Faculty grades submission (CFR-LMS-010)
    Purpose: Verify that Faculty can grade an individual student submission
    by entering points and feedback.
    """
    _asg, sub = _setup_grading_env(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    resp = client.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "90.00",
            "feedback_text": "Good analysis",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["points_awarded"])) == Decimal("90.00")
    assert data["feedback_text"] == "Good analysis"

    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.points_awarded == Decimal("90.00")
    assert grade.feedback_text == "Good analysis"


def test_tc_fr_030_ta_grades_submission(stub_iam):
    """Test ID: TC-FR-030.

    Source ID: AFR-LMS-010.2: TA grades submission (CFR-LMS-010)
    Purpose: Verify that an assigned TA can grade an individual student submission
    by entering points and feedback.
    """
    _asg, sub = _setup_grading_env(101)
    client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "85.00",
            "feedback_text": "Well structured",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["points_awarded"])) == Decimal("85.00")
    assert data["feedback_text"] == "Well structured"

    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.points_awarded == Decimal("85.00")
    assert grade.feedback_text == "Well structured"


def test_tc_fr_031_attribute_grading_action(stub_iam):
    """Test ID: TC-FR-031.

    Source ID: AFR-LMS-010.3: Attribute grading action (CFR-LMS-010)
    Purpose: Verify that the system records the identity of the Faculty member
    or TA performing the grading action.
    """
    _asg, sub = _setup_grading_env(101)
    client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "88.00",
            "feedback_text": "Graded by TA",
        },
        format="json",
    )
    assert resp.status_code == 200

    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.graded_by == 3001


def test_tc_fr_032_hold_grade_in_draft(stub_iam):
    """Test ID: TC-FR-032.

    Source ID: AFR-LMS-011.1: Hold grade in draft (CFR-LMS-011)
    Purpose: Verify that entered grade and feedback are kept in Draft state until released.
    """
    _asg, sub = _setup_grading_env(101)
    client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")

    resp = client.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "92.00",
            "feedback_text": "Draft evaluation",
        },
        format="json",
    )
    assert resp.status_code == 200

    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.status == GradeStatus.DRAFT


def test_tc_fr_033_hide_draft_grade_from_student(stub_iam):
    """Test ID: TC-FR-033.

    Source ID: AFR-LMS-011.2: Hide draft grade from Student (CFR-LMS-011)
    Purpose: Verify that students are prevented from viewing draft grades and
    feedback prior to release.
    """
    _asg, sub = _setup_grading_env(101)
    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("88.00"),
        feedback_text="Unreleased notes",
        status=GradeStatus.DRAFT,
        graded_by=2001,
    )

    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    resp = stu_client.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp.status_code == 404


def test_tc_fr_034_faculty_releases_grade_feedback(stub_iam):
    """Test ID: TC-FR-034.

    Source ID: AFR-LMS-011.3: Faculty releases grade/feedback (CFR-LMS-011)
    Purpose: Verify that Faculty can release draft grades and feedback to students.
    """
    asg, sub = _setup_grading_env(101)
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("94.00"),
        feedback_text="Great work on this task.",
        status=GradeStatus.DRAFT,
        graded_by=2001,
    )

    fac_client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    resp = fac_client.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["published_count"] >= 1

    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED

    # Student can now access released grade
    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    stu_resp = stu_client.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert stu_resp.status_code == 200
    assert Decimal(str(stu_resp.json()["points_awarded"])) == Decimal("94.00")


def test_tc_fr_035_view_own_released_grade_feedback(stub_iam):
    """Test ID: TC-FR-035.

    Source ID: AFR-LMS-012.1: View own released grade/feedback (CFR-LMS-012)
    Purpose: Verify that a Student can view their own grade and feedback after release.
    """
    _asg, sub = _setup_grading_env(101)
    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("95.00"),
        feedback_text="Comprehensive and well-written.",
        status=GradeStatus.PUBLISHED,
        graded_by=2001,
        published_by=2001,
        published_at=timezone.now(),
    )

    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")
    resp = stu_client.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(str(data["points_awarded"])) == Decimal("95.00")
    assert data["feedback_text"] == "Comprehensive and well-written."


def test_tc_fr_036_released_grade_is_read_only_to_student(stub_iam):
    """Test ID: TC-FR-036.

    Source ID: AFR-LMS-012.2: Released grade is read-only to Student (CFR-LMS-012)
    Purpose: Verify that released grade and feedback are presented to the Student
    in read-only form without edit permissions.
    """
    _asg, sub = _setup_grading_env(101)
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("80.00"),
        feedback_text="Solid submission.",
        status=GradeStatus.PUBLISHED,
        graded_by=2001,
        published_by=2001,
        published_at=timezone.now(),
    )

    stu_client = _make_client(stub_iam, user_id=1001, perms=_STUDENT, kind="student", role="student")

    # Student attempts to modify their grade
    resp = stu_client.patch(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "100.00",
            "feedback_text": "Hacked full marks",
        },
        format="json",
    )
    assert resp.status_code == 403

    grade.refresh_from_db()
    assert grade.points_awarded == Decimal("80.00")


def test_tc_fr_037_log_post_release_grade_change_actor(stub_iam):
    """Test ID: TC-FR-037.

    Source ID: AFR-LMS-013.1: Log post-release grade change actor (CFR-LMS-013)
    Purpose: Verify that the system logs the identity of the actor who modifies
    a previously released grade.
    """
    _asg, sub = _setup_grading_env(101)
    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("85.00"),
        feedback_text="Initial grading.",
        status=GradeStatus.PUBLISHED,
        graded_by=2001,
        published_by=2001,
        published_at=timezone.now(),
    )

    fac_client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    resp = fac_client.patch(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "90.00",
            "feedback_text": "Revised after regrade request.",
            "reason": "Re-evaluation of problem 3.",
        },
        format="json",
    )
    assert resp.status_code == 200

    audit = GradeChangeAudit.objects.filter(submission_id=sub.id).first()
    assert audit is not None
    assert audit.changed_by == 2001
    assert audit.old_points == Decimal("85.00")
    assert audit.new_points == Decimal("90.00")


def test_tc_fr_038_log_post_release_grade_change_time(stub_iam):
    """Test ID: TC-FR-038.

    Source ID: AFR-LMS-013.2: Log post-release grade change time (CFR-LMS-013)
    Purpose: Verify that the system logs the timestamp when a released grade is changed.
    """
    _asg, sub = _setup_grading_env(101)
    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("75.00"),
        feedback_text="Original score.",
        status=GradeStatus.PUBLISHED,
        graded_by=2001,
        published_by=2001,
        published_at=timezone.now(),
    )

    fac_client = _make_client(stub_iam, user_id=2001, perms=_FACULTY, kind="faculty", role="faculty")
    before_mod = timezone.now()
    resp = fac_client.patch(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "82.00",
            "reason": "Correction of grading rubric.",
        },
        format="json",
    )
    after_mod = timezone.now()
    assert resp.status_code == 200

    audit = GradeChangeAudit.objects.filter(submission_id=sub.id).first()
    assert audit is not None
    assert before_mod - timedelta(seconds=2) <= audit.changed_at <= after_mod + timedelta(seconds=2)

    # Verify retrieval via audit API
    audit_resp = fac_client.get(f"/api/v1/lms/submissions/{sub.id}/grade-audit/")
    assert audit_resp.status_code == 200
    audits_data = audit_resp.json()
    assert len(audits_data) >= 1
    assert audits_data[0]["changed_at"] is not None
