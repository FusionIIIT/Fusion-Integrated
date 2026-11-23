"""Tests for LMS business services and use case workflows."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import DomainError, PermissionDeniedError
from modules.lms import services
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
    GradeChangeAudit,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_course():
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=301,
        course_code="CS501",
        title="Advanced Algorithms",
        syllabus="Flows, LP, NP-Completeness",
    )
    # Instructor: user 4001
    CourseMembership.objects.create(
        course_id=301,
        user_id=4001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA with announcement & grade authority: user 4002
    CourseMembership.objects.create(
        course_id=301,
        user_id=4002,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=True,
        can_grade=True,
    )
    # TA without announcement authority: user 4003
    CourseMembership.objects.create(
        course_id=301,
        user_id=4003,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=False,
        can_grade=True,
    )
    # TA without grading authority: user 4004
    CourseMembership.objects.create(
        course_id=301,
        user_id=4004,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=True,
        can_grade=False,
    )
    # Student: user 5001
    CourseMembership.objects.create(
        course_id=301,
        user_id=5001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws, now


def test_workspace_service(base_course):
    _ws, _ = base_course
    p_inst = make_principal(user_id=4001, kind="faculty", active_role="faculty")
    p_student = make_principal(user_id=5001)

    # Instructor updates syllabus
    updated = services.update_course_details(
        course_id=301,
        syllabus="Updated Syllabus: Flows, Approximation",
        schedule_info="Tue/Thu 2-3:30 PM",
        principal=p_inst,
    )
    assert updated.syllabus == "Updated Syllabus: Flows, Approximation"

    # Student cannot update details
    with pytest.raises(PermissionDeniedError):
        services.update_course_details(
            course_id=301,
            syllabus="Hacked Syllabus",
            schedule_info="Never",
            principal=p_student,
        )


def test_materials_service(base_course):
    _, now = base_course
    p_inst = make_principal(user_id=4001, kind="faculty", active_role="faculty")
    p_student = make_principal(user_id=5001)

    # Immediate material
    mat1 = services.create_material(
        course_id=301,
        title="Syllabus PDF",
        description="Course syllabus",
        material_type=MaterialType.LINK,
        content_text=None,
        external_url="https://example.com/syllabus.pdf",
        file_attachment=None,
        section_name="General",
        sort_order=1,
        release_date=None,
        principal=p_inst,
    )
    assert mat1.status == MaterialStatus.PUBLISHED

    # Future scheduled material
    future_date = now + timedelta(days=3)
    mat2 = services.create_material(
        course_id=301,
        title="Quiz 1 Prep",
        description="Prep material",
        material_type=MaterialType.NOTE,
        content_text="Read chapter 4 and 5",
        external_url=None,
        file_attachment=None,
        section_name="Week 2",
        sort_order=2,
        release_date=future_date,
        principal=p_inst,
    )
    assert mat2.status == MaterialStatus.SCHEDULED

    # Non-instructor cannot create material
    with pytest.raises(PermissionDeniedError):
        services.create_material(
            course_id=301,
            title="Unauthorized",
            description="",
            material_type=MaterialType.NOTE,
            content_text="Unauthorized note",
            external_url=None,
            file_attachment=None,
            section_name="General",
            sort_order=3,
            release_date=None,
            principal=p_student,
        )

    # Delete material
    services.delete_material(mat1.id, p_inst)
    assert not CourseMaterial.objects.filter(id=mat1.id).exists()


def test_announcements_service_ta_authorization(base_course):
    _, _ = base_course
    p_inst = make_principal(user_id=4001, kind="faculty", active_role="faculty")
    p_ta_allowed = make_principal(user_id=4002)
    p_ta_forbidden = make_principal(user_id=4003)
    p_student = make_principal(user_id=5001)

    # Instructor posts announcement
    ann1 = services.post_announcement(
        course_id=301,
        title="Exam schedule",
        content="Midterm on Oct 15",
        principal=p_inst,
    )
    assert ann1.author_role == CourseRole.INSTRUCTOR

    # TA with can_post_announcement=True
    ann2 = services.post_announcement(
        course_id=301,
        title="Office hours update",
        content="Hours moved to 4 PM",
        principal=p_ta_allowed,
    )
    assert ann2.author_role == CourseRole.TA

    # TA with can_post_announcement=False raises PermissionDenied
    with pytest.raises(PermissionDeniedError, match="permission to post announcements"):
        services.post_announcement(
            course_id=301,
            title="TA Unauthorized",
            content="Should fail",
            principal=p_ta_forbidden,
        )

    # Student raises PermissionDenied
    with pytest.raises(PermissionDeniedError):
        services.post_announcement(
            course_id=301,
            title="Student Announcement",
            content="Spam",
            principal=p_student,
        )


def test_assignments_and_submissions_workflow(base_course):
    _, now = base_course
    p_inst = make_principal(user_id=4001, kind="faculty", active_role="faculty")
    p_student = make_principal(user_id=5001)

    # 1. Instructor creates assignment in DRAFT
    ass = services.create_assignment(
        course_id=301,
        title="Assignment 1: Max Flow",
        instructions="Implement Edmonds-Karp",
        points_possible=100.0,
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        release_date=None,
        principal=p_inst,
    )
    assert ass.status == AssignmentStatus.DRAFT

    # 2. Publish assignment immediately
    published_ass = services.publish_assignment(
        assignment_id=ass.id,
        release_date=None,
        principal=p_inst,
    )
    assert published_ass.status == AssignmentStatus.PUBLISHED

    # 3. Student submits on time
    sub = services.submit_assignment(
        assignment_id=ass.id,
        submission_type=SubmissionType.TEXT,
        content_text="def edmonds_karp(): ...",
        content_link=None,
        file_attachment=None,
        principal=p_student,
    )
    assert sub.id is not None
    assert sub.student_id == 5001

    # 4. Student attempting submission of wrong type raises ValueError (BR-LMS-012)
    with pytest.raises((ValueError, DomainError), match="must match assignment configuration"):
        services.submit_assignment(
            assignment_id=ass.id,
            submission_type=SubmissionType.FILE,
            content_text=None,
            content_link=None,
            file_attachment=None,
            principal=p_student,
        )

    # 5. Submission past due date raises ValueError (BR-LMS-013)
    past_ass = Assignment.objects.create(
        course_id=301,
        title="Past Assignment",
        instructions="Expired",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now - timedelta(days=1),  # past due
        status=AssignmentStatus.PUBLISHED,
        created_by=4001,
    )
    with pytest.raises((ValueError, DomainError), match="deadline has passed"):
        services.submit_assignment(
            assignment_id=past_ass.id,
            submission_type=SubmissionType.TEXT,
            content_text="Late work",
            content_link=None,
            file_attachment=None,
            principal=p_student,
        )


def test_grading_audit_and_release_workflow(base_course):
    """Grading workflow, audit trail, and release verification (BR-LMS-015, BR-LMS-017, BR-LMS-019)."""
    _, now = base_course
    p_inst = make_principal(user_id=4001, kind="faculty", active_role="faculty")
    p_ta_grader = make_principal(user_id=4002)
    p_ta_no_grade = make_principal(user_id=4004)

    ass = Assignment.objects.create(
        course_id=301,
        title="Lab 3",
        instructions="Do lab",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=4001,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=ass,
        student_id=5001,
        submission_type=SubmissionType.TEXT,
        content_text="Solution",
    )

    # 1. TA without grading authority cannot grade
    with pytest.raises(PermissionDeniedError, match="grading authority"):
        services.grade_submission(
            submission_id=sub.id,
            points_awarded=80,
            feedback_text="Good",
            principal=p_ta_no_grade,
        )

    # 2. Authorized TA grades submission -> saved as DRAFT (BR-LMS-015: attribution recorded)
    grade = services.grade_submission(
        submission_id=sub.id,
        points_awarded=88.5,
        feedback_text="Initial draft grade",
        principal=p_ta_grader,
    )
    assert grade.status == GradeStatus.DRAFT
    assert grade.points_awarded == Decimal("88.5")
    assert grade.graded_by == 4002

    # 3. TA updates draft grade before release -> NO audit record generated
    services.update_grade(
        submission_id=sub.id,
        points_awarded=90.0,
        feedback_text="Corrected draft grade",
        reason="Minor recheck before release",
        principal=p_ta_grader,
    )
    assert not GradeChangeAudit.objects.filter(submission_id=sub.id).exists()

    # 4. TA attempts to publish grades -> FAILS (Faculty only BR-LMS-017)
    with pytest.raises(PermissionDeniedError, match="Only assigned instructors"):
        services.publish_grades(
            assignment_id=ass.id,
            submission_ids=[sub.id],
            principal=p_ta_grader,
        )

    # 5. Instructor publishes grades -> succeeds
    published_count = services.publish_grades(
        assignment_id=ass.id,
        submission_ids=[sub.id],
        principal=p_inst,
    )
    assert published_count == 1
    grade.refresh_from_db()
    assert grade.status == GradeStatus.PUBLISHED

    # 6. Post-release grade change by instructor -> AUTOMATIC GradeChangeAudit (BR-LMS-019)
    services.update_grade(
        submission_id=sub.id,
        points_awarded=95.0,
        feedback_text="Re-evaluated question 3 after appeal",
        reason="Student submitted valid clarification on question 3",
        principal=p_inst,
    )
    grade.refresh_from_db()
    assert grade.points_awarded == Decimal("95.0")

    audits = GradeChangeAudit.objects.filter(submission_id=sub.id)
    assert audits.count() == 1
    audit = audits.first()
    assert audit.old_points == Decimal("90.0")
    assert audit.new_points == Decimal("95.0")
    assert audit.changed_by == 4001
    assert "clarification" in audit.reason
