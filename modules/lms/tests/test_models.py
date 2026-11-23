"""Tests for LMS database models and constraints."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
    GradeChangeAudit,
    SubmissionGrade,
)

pytestmark = pytest.mark.django_db


def test_course_workspace_model():
    ws = CourseWorkspace.objects.create(
        course_id=101,
        course_code="CS301",
        title="Operating Systems",
        syllabus="Processes, Threads, Concurrency",
        schedule_info="MWF 10-11 AM",
    )
    assert ws.id is not None
    assert str(ws) == "CS301: Operating Systems"

    # Unique course_id constraint
    with pytest.raises(IntegrityError), transaction.atomic():
        CourseWorkspace.objects.create(course_id=101, course_code="CS301B", title="Another OS")


def test_course_membership_unique_role_constraint():
    m = CourseMembership.objects.create(
        course_id=101,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    assert str(m) == "Course 101 - User 1001 (STUDENT)"

    # Duplicate course, user, role violates unique constraint
    with pytest.raises(IntegrityError), transaction.atomic():
        CourseMembership.objects.create(
            course_id=101,
            user_id=1001,
            role=CourseRole.STUDENT,
        )

    # Different role for same user in same course is permitted (e.g. TA and Student if valid)
    m2 = CourseMembership.objects.create(
        course_id=101,
        user_id=1001,
        role=CourseRole.TA,
        can_grade=True,
    )
    assert m2.id is not None


def test_course_material_model():
    mat = CourseMaterial.objects.create(
        course_id=101,
        title="Lecture 1 Slides",
        material_type=MaterialType.LINK,
        external_url="https://example.com/slides",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=2001,
    )
    assert str(mat) == "Lecture 1 Slides (LINK)"
    assert mat.status == MaterialStatus.PUBLISHED


def test_course_announcement_model():
    """BR-LMS-008: Announcements are automatically timestamped upon creation and scoped to course audience."""
    ann = CourseAnnouncement.objects.create(
        course_id=101,
        title="Welcome to CS301",
        content="Classes begin tomorrow.",
        author_id=2001,
        author_role=CourseRole.INSTRUCTOR,
    )
    assert str(ann) == "Welcome to CS301 (Course 101)"
    assert ann.created_at is not None
    assert ann.course_id == 101


def test_assignment_points_positive_constraint():
    now = timezone.now()
    due = now + timedelta(days=7)

    # Valid points
    a = Assignment.objects.create(
        course_id=101,
        title="Lab 1",
        instructions="Complete the tasks",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.FILE,
        due_date=due,
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )
    assert str(a) == "Lab 1 (Course 101)"

    # Points <= 0 violates CheckConstraint
    with pytest.raises(IntegrityError):
        Assignment.objects.create(
            course_id=101,
            title="Invalid Points Lab",
            instructions="Invalid",
            points_possible=Decimal("0.00"),
            submission_type=SubmissionType.FILE,
            due_date=due,
            status=AssignmentStatus.DRAFT,
            created_by=2001,
        )


def test_assignment_due_after_release_constraint():
    now = timezone.now()
    release = now + timedelta(days=5)
    due = now + timedelta(days=2)  # due BEFORE release!

    with pytest.raises(IntegrityError):
        Assignment.objects.create(
            course_id=101,
            title="Broken Dates Lab",
            instructions="Broken",
            points_possible=Decimal("20.00"),
            submission_type=SubmissionType.FILE,
            due_date=due,
            release_date=release,
            status=AssignmentStatus.SCHEDULED,
            created_by=2001,
        )


def test_submission_and_grade_constraints():
    now = timezone.now()
    a = Assignment.objects.create(
        course_id=101,
        title="Lab 2",
        instructions="Do lab 2",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        created_by=2001,
    )

    sub = AssignmentSubmission.objects.create(
        assignment=a,
        student_id=1001,
        submission_type=SubmissionType.TEXT,
        content_text="My answer",
        status=SubmissionStatus.SUBMITTED,
    )
    assert "Submission" in str(sub)

    # Valid grade
    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("95.00"),
        feedback_text="Great work!",
        status=GradeStatus.PUBLISHED,
        graded_by=2001,
    )
    assert "Grade for Submission" in str(grade)

    # Negative points awarded violates constraint
    sub2 = AssignmentSubmission.objects.create(
        assignment=a,
        student_id=1002,
        submission_type=SubmissionType.TEXT,
        content_text="Another answer",
        status=SubmissionStatus.SUBMITTED,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        SubmissionGrade.objects.create(
            submission=sub2,
            points_awarded=Decimal("-5.00"),
            status=GradeStatus.DRAFT,
            graded_by=2001,
        )

    # Grade Change Audit
    audit = GradeChangeAudit.objects.create(
        grade=grade,
        submission_id=sub.id,
        old_points=Decimal("95.00"),
        new_points=Decimal("98.00"),
        old_feedback="Great work!",
        new_feedback="Re-evaluated bonus points.",
        changed_by=2001,
        reason="Grade recheck request approved.",
    )
    assert str(audit).startswith("Audit for Grade")
