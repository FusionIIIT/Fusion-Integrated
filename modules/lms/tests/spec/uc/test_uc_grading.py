"""Specification use case tests for LMS Grading and Grade Release.

Covers:
- TC-UC-032 / UC-LMS-012 Main Flow: Faculty or TA grades student submission
- TC-UC-033 / UC-LMS-012 Alternative A1: Changing released grade creates audit record
- TC-UC-034 / UC-LMS-012 Exception E1: Unauthorized grader rejected
- TC-UC-035 / UC-LMS-013 Main Flow: Faculty releases draft grades and feedback
- TC-UC-036 / UC-LMS-013 Exception E1: TA cannot perform grade release
- TC-UC-037 / UC-LMS-014 Main Flow: Student views own released grade read-only
- TC-UC-038 / UC-LMS-014 Alternative A1: Draft or unreleased grades omitted from students
- TC-UC-039 / UC-LMS-014 Exception E1: Access to another student's grade denied
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


def _setup_grading_world(course_id: int = 101):
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Compilers",
        syllabus="Lexing, Parsing, Code Gen",
        schedule_info="MWF 09:00",
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
        title="Project 1: Parser",
        instructions="Implement LL(1) parser",
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
        content_text="Parser AST implementation",
        attempt_number=1,
    )

    return {
        "workspace": ws,
        "assignment": asg,
        "submission": sub,
    }


def test_tc_uc_032_faculty_or_ta_grades_submission(stub_iam):
    """Test ID: TC-UC-032.

    Source ID: UC-LMS-012 Main Flow
    Purpose: Verify that assigned Faculty or TA can grade a student submission,
    entering points and feedback stored in Draft state with actor attribution.
    """
    world = _setup_grading_world(101)
    sub = world["submission"]

    # Grader G1: TA (user_id 201)
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client_ta.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "85.00",
            "feedback_text": "Good work on the parser grammar.",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(str(data["points_awarded"])) == Decimal("85.00")
    assert data["feedback_text"] == "Good work on the parser grammar."
    assert data["graded_by"] == 201
    assert data["status"] == GradeStatus.DRAFT

    # Verified in DB
    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.points_awarded == Decimal("85.00")
    assert grade.graded_by == 201
    assert grade.status == GradeStatus.DRAFT


def test_tc_uc_033_changing_released_grade_creates_audit_record(stub_iam):
    """Test ID: TC-UC-033.

    Source ID: UC-LMS-012 Alternative A1
    Purpose: Verify that changing a released grade creates an audit record
    capturing actor identity and timestamp.
    """
    world = _setup_grading_world(101)
    sub = world["submission"]
    now = timezone.now()

    # Precondition: Grade was previously released
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("85.00"),
        feedback_text="Initial grading",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now - timedelta(hours=2),
    )

    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client_fac.patch(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "90.00",
            "feedback_text": "Revised after regrade request.",
            "reason": "Regrade after review",
        },
        format="json",
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["points_awarded"])) == Decimal("90.00")

    # Verify audit record created
    audits = GradeChangeAudit.objects.filter(grade=grade)
    assert audits.count() == 1
    audit = audits.first()
    assert audit.changed_by == 101
    assert audit.old_points == Decimal("85.00")
    assert audit.new_points == Decimal("90.00")
    assert audit.changed_at is not None


def test_tc_uc_034_unauthorized_grader_rejected(stub_iam):
    """Test ID: TC-UC-034.

    Source ID: UC-LMS-012 Exception E1
    Purpose: Verify that a grading attempt by an unauthorized grader not
    assigned to the course is rejected.
    """
    world = _setup_grading_world(101)
    sub = world["submission"]

    # User U_unauth (user_id 777) has faculty perms but is not assigned to Course 101
    client_unauth = _make_client(
        stub_iam, user_id=777, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client_unauth.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "95.00",
            "feedback_text": "Unauthorized evaluation",
        },
        format="json",
    )
    assert resp.status_code == 403

    # Commits no grade changes
    assert SubmissionGrade.objects.filter(submission=sub).count() == 0


def test_tc_uc_035_faculty_releases_draft_grades(stub_iam):
    """Test ID: TC-UC-035.

    Source ID: UC-LMS-013 Main Flow
    Purpose: Verify that assigned Faculty can release draft grades and feedback,
    making them visible to students.
    """
    world = _setup_grading_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    # Draft grade exists
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("88.00"),
        feedback_text="Solid AST implementation.",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

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

    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101
    assert grade.published_at is not None

    # Released grades now available to corresponding student S1
    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_s1.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_student.status_code == 200
    grade_data = resp_student.json()
    assert Decimal(str(grade_data["points_awarded"])) == Decimal("88.00")
    assert grade_data["feedback_text"] == "Solid AST implementation."


def test_tc_uc_036_ta_cannot_perform_grade_release(stub_iam):
    """Test ID: TC-UC-036.

    Source ID: UC-LMS-013 Exception E1
    Purpose: Verify that a Teaching Assistant (TA) cannot perform grade release
    under the baseline specification.
    """
    world = _setup_grading_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("88.00"),
        feedback_text="Draft feedback.",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    # TA T1 attempts release
    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client_ta.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp.status_code == 403

    # Grades remain in DRAFT
    grade.refresh_from_db()
    assert grade.status == GradeStatus.DRAFT

    # Hidden from student
    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_s1.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_student.status_code == 404


def test_tc_uc_037_student_views_own_released_grade_read_only(stub_iam):
    """Test ID: TC-UC-037.

    Source ID: UC-LMS-014 Main Flow
    Purpose: Verify that an enrolled Student can view their own released grade
    and feedback in read-only form.
    """
    world = _setup_grading_world(101)
    asg = world["assignment"]
    sub = world["submission"]
    now = timezone.now()

    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("94.00"),
        feedback_text="Excellent parser tests.",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # 1. Retrieve via submission grade detail
    resp_detail = client_s1.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_detail.status_code == 200
    grade_data = resp_detail.json()
    assert Decimal(str(grade_data["points_awarded"])) == Decimal("94.00")
    assert grade_data["feedback_text"] == "Excellent parser tests."

    # 2. Assignment-level roster query from student standpoint returns empty (staff-only)
    resp_list = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/grades/")
    assert resp_list.status_code == 200
    assert resp_list.json() == []

    # 3. Read-only verification: Student cannot edit grade
    resp_write = client_s1.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={"points_awarded": "100.00"},
        format="json",
    )
    assert resp_write.status_code == 403


def test_tc_uc_038_draft_grades_omitted_from_students(stub_iam):
    """Test ID: TC-UC-038.

    Source ID: UC-LMS-014 Alternative A1
    Purpose: Verify that draft or unreleased grades are omitted and not shown
    to Students.
    """
    world = _setup_grading_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    # Grade is stored in Draft state
    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("75.00"),
        feedback_text="Preliminary draft feedback",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Assignment grades list returns empty for student
    resp_list = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/grades/")
    assert resp_list.status_code == 200
    assert resp_list.json() == []

    # Submission grade detail returns 404 for student
    resp_detail = client_s1.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp_detail.status_code == 404


def test_tc_uc_039_student_denied_access_to_other_student_grade(stub_iam):
    """Test ID: TC-UC-039.

    Source ID: UC-LMS-014 Exception E1
    Purpose: Verify that access to another student's grade or feedback is denied.
    """
    world = _setup_grading_world(101)
    asg = world["assignment"]
    sub_s1 = world["submission"]
    now = timezone.now()

    # S1 has a released grade
    SubmissionGrade.objects.create(
        submission=sub_s1,
        points_awarded=Decimal("95.00"),
        feedback_text="S1 Great job",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now,
    )

    # Student S2 (user_id 302) attempts to view S1's grade
    client_s2 = _make_client(
        stub_iam, user_id=302, perms=_STUDENT, kind="student", role="student"
    )

    # S2 direct access to S1's grade-detail returns 404
    resp_detail = client_s2.get(f"/api/v1/lms/submissions/{sub_s1.id}/grade-detail/")
    assert resp_detail.status_code == 404

    # S2 querying assignment grades list does not expose S1's grade
    resp_list = client_s2.get(f"/api/v1/lms/assignments/{asg.id}/grades/")
    assert resp_list.status_code == 200
    assert resp_list.json() == []
