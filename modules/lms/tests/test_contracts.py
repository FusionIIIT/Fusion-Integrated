"""Tests for LMS contracts.py plural cross-module getters."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.lms import contracts
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

pytestmark = pytest.mark.django_db


def test_contracts_plural_getters():
    now = timezone.now()
    CourseWorkspace.objects.create(
        course_id=901,
        course_code="CS101",
        title="Intro to CS",
        syllabus="Basics",
    )
    CourseWorkspace.objects.create(
        course_id=902,
        course_code="CS102",
        title="Data Structures",
        syllabus="Trees, Graphs",
    )

    # Memberships
    CourseMembership.objects.create(
        course_id=901,
        user_id=101,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=902,
        user_id=101,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=901,
        user_id=102,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )

    # Assignments and Grades
    ass = Assignment.objects.create(
        course_id=901,
        title="Assignment 1",
        instructions="Instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=1,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=ass,
        student_id=101,
        submission_type=SubmissionType.TEXT,
        content_text="Solution",
    )
    SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("95.00"),
        feedback_text="Great work",
        status=GradeStatus.PUBLISHED,
        graded_by=1,
        published_at=now,
    )

    # 1. get_course_summaries
    summaries = contracts.get_course_summaries([901, 902, 999])
    assert 901 in summaries
    assert 902 in summaries
    assert 999 not in summaries
    assert summaries[901].course_code == "CS101"
    assert summaries[902].course_code == "CS102"

    # Empty query
    assert contracts.get_course_summaries([]) == {}

    # 2. get_user_course_enrollments
    enrollments = contracts.get_user_course_enrollments([101, 102, 999])
    assert len(enrollments[101]) == 2
    assert len(enrollments[102]) == 1
    assert enrollments[999] == []

    # Empty query
    assert contracts.get_user_course_enrollments([]) == {}

    # 3. get_student_course_grades
    grades = contracts.get_student_course_grades(student_ids=[101, 102], course_id=901)
    assert len(grades[101]) == 1
    assert grades[101][0].points_awarded == 95.0
    assert grades[102] == []

    # Empty query
    assert contracts.get_student_course_grades([]) == {}
