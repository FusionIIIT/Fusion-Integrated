"""Specification business rule tests for LMS Grading and Grade Release.

Covers:
- TC-BR-031 / BR-LMS-015 permitted (Faculty): Faculty permitted to grade, action attributed
- TC-BR-032 / BR-LMS-015 permitted (TA): TA permitted to grade, action attributed
- TC-BR-033 / BR-LMS-015 prohibited: Non-staff prohibited from grading
- TC-BR-034 / BR-LMS-016 permitted: Released grades visible to students
- TC-BR-035 / BR-LMS-016 prohibited: Draft grades concealed from students
- TC-BR-036 / BR-LMS-017 permitted: Faculty authorized to release draft grades
- TC-BR-037 / BR-LMS-017 prohibited: TA prohibited from grade release
- TC-BR-038 / BR-LMS-018 permitted: Student views own released grade read-only
- TC-BR-039 / BR-LMS-018 prohibited (modification): Student prohibited from altering grade
- TC-BR-040 / BR-LMS-018 prohibited (other student grade): Student prohibited from peer grade
- TC-BR-041 / BR-LMS-019 permitted: Changing released grade creates audit record
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
from modules.lms.registry import _FACULTY, _OBSERVER, _STUDENT, _TA

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
        title="Software Security",
        syllabus="Memory Safety, Web Security, Fuzzing",
        schedule_info="MWF 14:00",
    )
    # Faculty
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA
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
    # Observer
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=401,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )

    asg = Assignment.objects.create(
        course_id=course_id,
        title="Fuzzing Lab",
        instructions="Fuzz binary for vulnerabilities",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub_s1 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="S1 AFL fuzzer crashes report",
        attempt_number=1,
    )

    sub_s2 = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=302,
        submission_type=SubmissionType.TEXT,
        content_text="S2 LibFuzzer crashes report",
        attempt_number=1,
    )

    return {
        "workspace": ws,
        "assignment": asg,
        "submission_s1": sub_s1,
        "submission_s2": sub_s2,
    }


def test_tc_br_031_faculty_permitted_to_grade_submission(stub_iam):
    """Test ID: TC-BR-031.

    Source ID: BR-LMS-015 permitted (Faculty)
    Purpose: Verify that an assigned Faculty member is permitted to grade
    submissions, and the grading action is attributed to the Faculty member.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]

    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client_fac.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "92.00",
            "feedback_text": "Good crash triage by Faculty",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(str(data["points_awarded"])) == Decimal("92.00")
    assert data["graded_by"] == 101
    assert data["status"] == GradeStatus.DRAFT

    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.points_awarded == Decimal("92.00")
    assert grade.graded_by == 101


def test_tc_br_032_ta_permitted_to_grade_submission(stub_iam):
    """Test ID: TC-BR-032.

    Source ID: BR-LMS-015 permitted (TA)
    Purpose: Verify that an assigned TA is permitted to grade submissions,
    and the grading action is attributed to the TA.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]

    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client_ta.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "88.00",
            "feedback_text": "Evaluated by TA",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()

    assert Decimal(str(data["points_awarded"])) == Decimal("88.00")
    assert data["graded_by"] == 201

    grade = SubmissionGrade.objects.get(submission=sub)
    assert grade.points_awarded == Decimal("88.00")
    assert grade.graded_by == 201


def test_tc_br_033_non_staff_prohibited_from_grading(stub_iam):
    """Test ID: TC-BR-033.

    Source ID: BR-LMS-015 prohibited
    Purpose: Verify that grading actions are prohibited for users not assigned
    as Faculty or TA for the course.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]

    # 1. Student attempting to grade
    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    assert (
        client_s1.post(
            f"/api/v1/lms/submissions/{sub.id}/grade/",
            data={"points_awarded": "100.00"},
            format="json",
        ).status_code
        == 403
    )

    # 2. Observer attempting to grade
    client_obs = _make_client(
        stub_iam, user_id=401, perms=_OBSERVER, kind="student", role="course_observer"
    )
    assert (
        client_obs.post(
            f"/api/v1/lms/submissions/{sub.id}/grade/",
            data={"points_awarded": "100.00"},
            format="json",
        ).status_code
        == 403
    )

    assert SubmissionGrade.objects.filter(submission=sub).count() == 0


def test_tc_br_034_released_grades_visible_to_student(stub_iam):
    """Test ID: TC-BR-034.

    Source ID: BR-LMS-016 permitted
    Purpose: Verify that grades and feedback become visible to the Student once released.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]
    now = timezone.now()

    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("94.00"),
        feedback_text="Released evaluation notes",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["points_awarded"])) == Decimal("94.00")
    assert data["feedback_text"] == "Released evaluation notes"


def test_tc_br_035_draft_grades_concealed_from_students(stub_iam):
    """Test ID: TC-BR-035.

    Source ID: BR-LMS-016 prohibited
    Purpose: Verify that grades and feedback in Draft state remain invisible
    and withheld from Students.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]

    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("85.00"),
        feedback_text="Unreleased draft feedback",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp.status_code == 404


def test_tc_br_036_faculty_authorized_to_release_draft_grades(stub_iam):
    """Test ID: TC-BR-036.

    Source ID: BR-LMS-017 permitted
    Purpose: Verify that assigned Faculty is authorized to release draft grades
    and feedback to Students.
    """
    world = _setup_grading_world(101)
    asg = world["assignment"]
    sub = world["submission_s1"]

    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("89.00"),
        feedback_text="Feedback pending release",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["published_count"] >= 1

    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED
    assert grade.published_by == 101


def test_tc_br_037_ta_prohibited_from_grade_release(stub_iam):
    """Test ID: TC-BR-037.

    Source ID: BR-LMS-017 prohibited
    Purpose: Verify that a Teaching Assistant (TA) is prohibited from releasing
    grades under the baseline specification.
    """
    world = _setup_grading_world(101)
    asg = world["assignment"]
    sub = world["submission_s1"]

    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("89.00"),
        feedback_text="Draft feedback",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client_ta.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub.id]},
        format="json",
    )
    assert resp.status_code == 403

    grade.refresh_from_db()
    assert grade.status == GradeStatus.DRAFT


def test_tc_br_038_student_views_released_grade_read_only(stub_iam):
    """Test ID: TC-BR-038.

    Source ID: BR-LMS-018 permitted
    Purpose: Verify that an enrolled Student is permitted to view their own
    released grade and feedback in read-only form.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]
    now = timezone.now()

    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("91.00"),
        feedback_text="Well done on fuzzing harness",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/")
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["points_awarded"])) == Decimal("91.00")
    assert resp.json()["feedback_text"] == "Well done on fuzzing harness"


def test_tc_br_039_student_prohibited_from_modifying_grade(stub_iam):
    """Test ID: TC-BR-039.

    Source ID: BR-LMS-018 prohibited (modification)
    Purpose: Verify that a Student is prohibited from modifying, editing, or
    tampering with their released grade or feedback.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]
    now = timezone.now()

    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("91.00"),
        feedback_text="Original feedback",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Student attempts POST grade
    assert (
        client_s1.post(
            f"/api/v1/lms/submissions/{sub.id}/grade/",
            data={"points_awarded": "100.00"},
            format="json",
        ).status_code
        == 403
    )

    # Student attempts PATCH grade
    assert (
        client_s1.patch(
            f"/api/v1/lms/submissions/{sub.id}/grade/",
            data={"points_awarded": "100.00"},
            format="json",
        ).status_code
        == 403
    )

    grade.refresh_from_db()
    assert grade.points_awarded == Decimal("91.00")


def test_tc_br_040_student_prohibited_from_peer_grade(stub_iam):
    """Test ID: TC-BR-040.

    Source ID: BR-LMS-018 prohibited (other student grade)
    Purpose: Verify that a Student is prohibited from viewing another student's
    released grade and feedback.
    """
    world = _setup_grading_world(101)
    sub_s2 = world["submission_s2"]
    now = timezone.now()

    SubmissionGrade.objects.create(
        submission=sub_s2,
        points_awarded=Decimal("98.00"),
        feedback_text="S2 Excellent crashes found",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now,
    )

    # Student S1 attempts to access S2's grade detail
    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.get(f"/api/v1/lms/submissions/{sub_s2.id}/grade-detail/")
    assert resp.status_code == 404


def test_tc_br_041_released_grade_change_logs_audit(stub_iam):
    """Test ID: TC-BR-041.

    Source ID: BR-LMS-019 permitted
    Purpose: Verify that whenever an already-released grade is changed, the system
    logs the change recording actor identity and timestamp.
    """
    world = _setup_grading_world(101)
    sub = world["submission_s1"]
    now = timezone.now()

    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("85.00"),
        feedback_text="Initial grading notes",
        status=GradeStatus.PUBLISHED,
        graded_by=201,
        published_by=101,
        published_at=now - timedelta(hours=3),
    )

    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    resp = client_fac.patch(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "93.00",
            "feedback_text": "Updated score after regrade",
            "reason": "Regrade appeal approved",
        },
        format="json",
    )
    assert resp.status_code == 200

    audits = GradeChangeAudit.objects.filter(grade=grade)
    assert audits.count() == 1
    audit = audits.first()
    assert audit.changed_by == 101
    assert audit.old_points == Decimal("85.00")
    assert audit.new_points == Decimal("93.00")
    assert audit.reason == "Regrade appeal approved"
    assert audit.changed_at is not None
