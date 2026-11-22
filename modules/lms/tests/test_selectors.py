"""Tests for LMS selectors and scoping (modules/lms/selectors/)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.http import Http404
from django.utils import timezone

from modules.lms.domain.entities import (
    CourseRole,
    MaterialType,
    SubmissionType,
)
from modules.lms.domain.errors import CourseAccessDenied, ObserverAccessViolation
from modules.lms.selectors import courses as sel
from modules.lms.selectors import scoping
from modules.lms.services import courses as service

pytestmark = pytest.mark.django_db


@pytest.fixture
def lms_data():
    now = timezone.now()
    course1 = service.create_course_workspace(
        course_code="CS101",
        title="Intro to CS",
        instructor_user_id=10,
        syllabus="Syllabus CS101",
    )
    course2 = service.create_course_workspace(
        course_code="CS102",
        title="Data Structures",
        instructor_user_id=10,
        syllabus="Syllabus CS102",
    )

    # Enroll user 100 as student in CS101
    service.enroll_member(
        course_id=course1.id,
        user_id=100,
        role=CourseRole.STUDENT.value,
    )
    # Enroll user 20 as TA in CS101
    service.enroll_member(
        course_id=course1.id,
        user_id=20,
        role=CourseRole.TA.value,
    )
    # Enroll user 30 as OBSERVER in CS101
    service.enroll_member(
        course_id=course1.id,
        user_id=30,
        role=CourseRole.OBSERVER.value,
    )

    # Add materials to CS101
    mat_pub = service.upload_course_material(
        course_id=course1.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Pub Mat",
        material_type=MaterialType.FILE.value,
        section_or_week="Sec 1",
        is_scheduled=False,
    )
    mat_sched = service.upload_course_material(
        course_id=course1.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Sched Mat",
        material_type=MaterialType.FILE.value,
        section_or_week="Sec 1",
        is_scheduled=True,
        scheduled_release_at=now + timedelta(days=2),
    )

    # Add announcement
    service.post_course_announcement(
        course_id=course1.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        can_post_announcements=True,
        title="Notice",
        content="Content",
    )

    # Add assignment
    assign = service.create_assignment(
        course_id=course1.id,
        user_id=10,
        user_role=CourseRole.FACULTY.value,
        title="Assign 1",
        instructions="Complete assignment",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=now + timedelta(days=2),
    )
    service.publish_assignment(
        assignment_id=assign.id,
        user_role=CourseRole.FACULTY.value,
    )

    # Student submission
    sub = service.submit_assignment(
        assignment_id=assign.id,
        student_user_id=100,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="solution",
    )

    # Grade submission
    grade = service.grade_submission(
        submission_id=sub.id,
        grader_user_id=10,
        grader_role=CourseRole.FACULTY.value,
        points=Decimal("95.00"),
        feedback="Great work",
    )

    return {
        "c1": course1,
        "c2": course2,
        "mat_pub": mat_pub,
        "mat_sched": mat_sched,
        "assign": assign,
        "sub": sub,
        "grade": grade,
    }


def test_get_user_courses_and_detail(lms_data):
    # Student 100 only sees CS101 membership
    memberships = sel.get_user_memberships(100)
    assert len(memberships) == 1
    assert memberships[0].course.course_code == "CS101"

    # Workspace detail
    ws = sel.get_course_workspace(lms_data["c1"].id, 100)
    assert ws.course_code == "CS101"

    with pytest.raises(CourseAccessDenied):
        sel.get_course_workspace(lms_data["c2"].id, 100)


def test_get_course_materials(lms_data):
    c1_id = lms_data["c1"].id

    # Faculty sees both published and scheduled
    faculty_mats = sel.get_course_materials(c1_id, CourseRole.FACULTY.value)
    assert len(faculty_mats) == 2

    # Student sees only published
    student_mats = sel.get_course_materials(c1_id, CourseRole.STUDENT.value)
    assert len(student_mats) == 1
    assert student_mats[0].title == "Pub Mat"


def test_get_course_assignments_and_submissions(lms_data):
    c1_id = lms_data["c1"].id
    assign_id = lms_data["assign"].id

    assignments = sel.get_course_assignments(c1_id, CourseRole.STUDENT.value)
    assert len(assignments) == 1

    # Student views submissions
    subs = sel.get_assignment_submissions(assign_id, 100, CourseRole.STUDENT.value)
    assert len(subs) == 1

    # Observer is restricted from viewing submissions
    with pytest.raises(ObserverAccessViolation):
        sel.get_assignment_submissions(assign_id, 30, CourseRole.OBSERVER.value)


def test_get_student_course_grades(lms_data):
    c1_id = lms_data["c1"].id
    assign_id = lms_data["assign"].id

    # Draft grade is hidden from student
    student_grades = sel.get_student_course_grades(c1_id, 100)
    assert len(student_grades) == 0

    # Release grade
    service.release_assignment_grades(
        assignment_id=assign_id,
        releaser_user_id=10,
        releaser_role=CourseRole.FACULTY.value,
    )

    # Now student sees released grade
    released_grades = sel.get_student_course_grades(c1_id, 100)
    assert len(released_grades) == 1
    assert released_grades[0].points == Decimal("95.00")


def test_get_submission_detail_and_logs(lms_data):
    sub = lms_data["sub"]
    # Student reads own submission detail
    found = sel.get_submission_detail(sub.id, 100, CourseRole.STUDENT.value)
    assert found is not None
    assert found.id == sub.id

    # Non-existent submission
    assert sel.get_submission_detail(99999, 100, CourseRole.STUDENT.value) is None

    # Grade change logs
    grade = lms_data["grade"]
    logs = sel.get_grade_change_logs(grade.id)
    assert logs.count() == 0


def test_scoping_functions(lms_data):
    c1 = lms_data["c1"]

    # Scope courses
    qs = scoping.scope_courses_for_user(100)
    assert qs.count() == 1

    # Visible course or 404
    found = scoping.get_visible_course_or_404(c1.id, 100)
    assert found.id == c1.id

    with pytest.raises(Http404):
        scoping.get_visible_course_or_404(lms_data["c2"].id, 100)

    # Scope submissions
    assign = lms_data["assign"]
    sub_qs = scoping.scope_submissions_for_user(assign.id, 100, CourseRole.STUDENT.value)
    assert sub_qs.count() == 1

    observer_qs = scoping.scope_submissions_for_user(assign.id, 30, CourseRole.OBSERVER.value)
    assert observer_qs.count() == 0
