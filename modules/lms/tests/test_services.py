"""Tests for LMS atomic domain services (modules/lms/services/courses.py)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.domain.errors import (
    InvalidAssignmentState,
    LmsDomainError,
    SubmissionTypeError,
    TAAuthoringRestriction,
    UnauthorizedGradingError,
)
from modules.lms.models import (
    GradeChangeLog,
)
from modules.lms.services import courses as service

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_course():
    return service.create_course_workspace(
        course_code="CS101",
        title="Intro to Computer Science",
        instructor_user_id=10,
        syllabus="Initial syllabus",
    )


def test_create_and_enroll(base_course):
    m_faculty = service.enroll_member(
        course_id=base_course.id,
        user_id=10,
        role=CourseRole.FACULTY.value,
        can_post_announcements=True,
    )
    assert m_faculty.role == CourseRole.FACULTY.value
    assert m_faculty.can_post_announcements is True

    m_student = service.enroll_member(
        course_id=base_course.id,
        user_id=100,
        role=CourseRole.STUDENT.value,
    )
    assert m_student.role == CourseRole.STUDENT.value


def test_material_lifecycle(base_course):
    now = timezone.now()
    mat = service.upload_course_material(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Week 1 Slides",
        material_type=MaterialType.FILE.value,
        section_or_week="Week 1",
        file_url="https://example.com/slides1.pdf",
        is_scheduled=False,
    )
    assert mat.status == MaterialStatus.PUBLISHED.value

    # Scheduled material
    sched_time = now + timedelta(days=2)
    sched_mat = service.upload_course_material(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Week 2 Slides",
        material_type=MaterialType.NOTE.value,
        section_or_week="Week 2",
        is_scheduled=True,
        scheduled_release_at=sched_time,
    )
    assert sched_mat.status == MaterialStatus.SCHEDULED.value


def test_announcements(base_course):
    service.enroll_member(
        course_id=base_course.id,
        user_id=10,
        role=CourseRole.FACULTY.value,
        can_post_announcements=True,
    )
    ann = service.post_course_announcement(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        can_post_announcements=True,
        title="Welcome to CS101",
        content="Please check syllabus.",
    )
    assert ann.title == "Welcome to CS101"

    # Unauthorized student post
    with pytest.raises(LmsDomainError):
        service.post_course_announcement(
            course_id=base_course.id,
            user_id=100,
            user_role=CourseRole.STUDENT.value,
            can_post_announcements=False,
            title="Spam",
            content="Spam",
        )


def test_assignment_lifecycle_and_submission(base_course):
    now = timezone.now()
    due = now + timedelta(days=5)

    assignment = service.create_assignment(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Homework 1",
        instructions="Write a python script",
        submission_type=SubmissionType.TEXT.value,
        points_possible=Decimal("100.00"),
        due_date=due,
    )
    assert assignment.status == AssignmentStatus.DRAFT.value

    # Student cannot submit while in draft
    with pytest.raises(InvalidAssignmentState):
        service.submit_assignment(
            assignment_id=assignment.id,
            student_user_id=100,
            student_role=CourseRole.STUDENT.value,
            submission_type=SubmissionType.TEXT.value,
            submission_content="result = 42",
        )

    # Publish assignment
    service.publish_assignment(
        assignment_id=assignment.id,
        user_role=CourseRole.FACULTY.value,
    )
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.AVAILABLE.value

    # Submission with wrong type
    with pytest.raises(SubmissionTypeError):
        service.submit_assignment(
            assignment_id=assignment.id,
            student_user_id=100,
            student_role=CourseRole.STUDENT.value,
            submission_type=SubmissionType.FILE.value,
            submission_content="file.pdf",
        )

    # Successful on-time submission
    sub = service.submit_assignment(
        assignment_id=assignment.id,
        student_user_id=100,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="result = 42",
    )
    assert sub.status == SubmissionStatus.SUBMITTED.value

    # Late submission test
    late_assignment = service.create_assignment(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Homework Past Due",
        instructions="Late work",
        submission_type=SubmissionType.TEXT.value,
        points_possible=Decimal("100.00"),
        due_date=now - timedelta(days=1),
    )
    service.publish_assignment(
        assignment_id=late_assignment.id,
        user_role=CourseRole.FACULTY.value,
    )
    late_sub = service.submit_assignment(
        assignment_id=late_assignment.id,
        student_user_id=100,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="late work",
    )
    assert late_sub.status == SubmissionStatus.LATE.value


def test_grading_and_release(base_course):
    now = timezone.now()
    assignment = service.create_assignment(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Lab 1",
        instructions="Complete lab",
        submission_type=SubmissionType.TEXT.value,
        points_possible=Decimal("50.00"),
        due_date=now + timedelta(days=3),
    )
    service.publish_assignment(
        assignment_id=assignment.id,
        user_role=CourseRole.FACULTY.value,
    )
    sub = service.submit_assignment(
        assignment_id=assignment.id,
        student_user_id=100,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="code",
    )

    # TA grades submission
    grade = service.grade_submission(
        submission_id=sub.id,
        grader_user_id=20,
        grader_role=CourseRole.TA.value,
        points=Decimal("45.00"),
        feedback="Good job",
    )
    assert grade.status == GradeStatus.DRAFT.value
    assert grade.points == Decimal("45.00")

    # TA cannot release grades (only Faculty can release)
    with pytest.raises(UnauthorizedGradingError):
        service.release_assignment_grades(
            assignment_id=assignment.id,
            releaser_user_id=20,
            releaser_role=CourseRole.TA.value,
        )

    # Faculty releases grades
    count = service.release_assignment_grades(
        assignment_id=assignment.id,
        releaser_user_id=10,
        releaser_role=CourseRole.FACULTY.value,
    )
    assert count == 1
    grade.refresh_from_db()
    assert grade.status == GradeStatus.RELEASED.value

    # Post-release grade modification by Faculty with audit trail
    mod_grade = service.modify_released_grade(
        grade_id=grade.id,
        modifier_user_id=10,
        modifier_role=CourseRole.FACULTY.value,
        new_points=Decimal("48.00"),
        reason="Re-evaluation of problem 2",
    )
    assert mod_grade.points == Decimal("48.00")

    audit = GradeChangeLog.objects.filter(grade=grade).first()
    assert audit is not None
    assert audit.old_points == Decimal("45.00")
    assert audit.new_points == Decimal("48.00")
    assert audit.reason == "Re-evaluation of problem 2"


def test_release_scheduled_items(base_course):
    now = timezone.now()
    past = now - timedelta(hours=1)
    future = now + timedelta(days=2)

    # Past scheduled material
    mat_past = service.upload_course_material(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Past Scheduled Mat",
        material_type=MaterialType.NOTE.value,
        section_or_week="Sec 1",
        is_scheduled=True,
        scheduled_release_at=past,
    )
    # Future scheduled material
    mat_future = service.upload_course_material(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Future Scheduled Mat",
        material_type=MaterialType.NOTE.value,
        section_or_week="Sec 2",
        is_scheduled=True,
        scheduled_release_at=future,
    )
    # Past scheduled assignment
    assign_past = service.create_assignment(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Past Scheduled Assignment",
        instructions="Desc",
        submission_type=SubmissionType.TEXT.value,
        points_possible=Decimal("100.00"),
        due_date=future,
    )
    service.publish_assignment(
        assignment_id=assign_past.id,
        user_role=CourseRole.FACULTY.value,
        is_scheduled=True,
        release_date=past,
    )

    released_count = service.release_scheduled_items()
    assert released_count >= 2

    mat_past.refresh_from_db()
    assert mat_past.status == MaterialStatus.PUBLISHED.value

    mat_future.refresh_from_db()
    assert mat_future.status == MaterialStatus.SCHEDULED.value

    assign_past.refresh_from_db()
    assert assign_past.status == AssignmentStatus.AVAILABLE.value


def test_service_error_branches(base_course):
    now = timezone.now()
    # TA attempting to upload material
    with pytest.raises(TAAuthoringRestriction):
        service.upload_course_material(
            course_id=base_course.id,
            user_id=20,
            user_role=CourseRole.TA.value,
            title="TA Mat",
        )
    # Student attempting to upload material
    with pytest.raises(LmsDomainError):
        service.upload_course_material(
            course_id=base_course.id,
            user_id=100,
            user_role=CourseRole.STUDENT.value,
            title="Stu Mat",
        )

    # TA attempting to create assignment
    with pytest.raises(TAAuthoringRestriction):
        service.create_assignment(
            course_id=base_course.id,
            user_id=20,
            user_role=CourseRole.TA.value,
            title="TA Assignment",
            instructions="Desc",
            points_possible=Decimal("100"),
            submission_type=SubmissionType.TEXT.value,
            due_date=now + timedelta(days=2),
        )
    # Student attempting to create assignment
    with pytest.raises(LmsDomainError):
        service.create_assignment(
            course_id=base_course.id,
            user_id=100,
            user_role=CourseRole.STUDENT.value,
            title="Stu Assignment",
            instructions="Desc",
            points_possible=Decimal("100"),
            submission_type=SubmissionType.TEXT.value,
            due_date=now + timedelta(days=2),
        )

    # Create valid assignment for further branch checks
    assign = service.create_assignment(
        course_id=base_course.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Check Branches",
        instructions="Desc",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=now + timedelta(days=2),
    )

    # TA attempting to publish
    with pytest.raises(TAAuthoringRestriction):
        service.publish_assignment(
            assignment_id=assign.id,
            user_role=CourseRole.TA.value,
        )
    # Student attempting to publish
    with pytest.raises(LmsDomainError):
        service.publish_assignment(
            assignment_id=assign.id,
            user_role=CourseRole.STUDENT.value,
        )

    # Publish properly
    service.publish_assignment(assignment_id=assign.id, user_role=CourseRole.FACULTY.value)

    # Faculty attempting to submit as student
    with pytest.raises(LmsDomainError):
        service.submit_assignment(
            assignment_id=assign.id,
            student_user_id=10,
            student_role=CourseRole.FACULTY.value,
            submission_type=SubmissionType.TEXT.value,
            submission_content="faculty submission",
        )

    # Student submits
    sub = service.submit_assignment(
        assignment_id=assign.id,
        student_user_id=100,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="solution",
    )

    # Points out of bounds (negative or exceeding points_possible)
    with pytest.raises(LmsDomainError):
        service.grade_submission(
            submission_id=sub.id,
            grader_user_id=10,
            grader_role=CourseRole.FACULTY.value,
            points=Decimal("-5.00"),
        )
    with pytest.raises(LmsDomainError):
        service.grade_submission(
            submission_id=sub.id,
            grader_user_id=10,
            grader_role=CourseRole.FACULTY.value,
            points=Decimal("60.00"),
        )

    # Draft grade modify before release
    grade = service.grade_submission(
        submission_id=sub.id,
        grader_user_id=10,
        grader_role=CourseRole.FACULTY.value,
        points=Decimal("40.00"),
    )
    with pytest.raises(LmsDomainError):
        service.modify_released_grade(
            grade_id=grade.id,
            modifier_user_id=10,
            modifier_role=CourseRole.FACULTY.value,
            new_points=Decimal("45.00"),
            reason="not released yet",
        )


def test_registry_and_schedule():
    from modules.lms import registry, schedule

    assert registry.MODULE["code"] == "lms"
    assert len(registry.NAV_ITEMS) == 4
    assert len(registry.PERMISSIONS) == 12
    assert "lms.publish-scheduled-content" in schedule.BEAT_SCHEDULE
