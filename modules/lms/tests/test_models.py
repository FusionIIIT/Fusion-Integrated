import pytest
from django.db import IntegrityError
from django.utils import timezone
from modules.lms.domain.constants import (
    Role,
    MaterialKind,
    ContentStatus,
    SubmissionType,
    SubmissionStatus,
    GradeStatus,
    GradeAction,
)
from modules.lms.models import (
    Course,
    CourseMembership,
    ModuleSection,
    CourseMaterial,
    Announcement,
    Assignment,
    Submission,
    Grade,
    GradeAuditLog,
)
from modules.lms.contracts import (
    get_courses,
    get_user_courses,
    get_course_memberships,
    get_assignments,
)

pytestmark = pytest.mark.django_db


def test_course_creation_and_attributes():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    assert course.code == 'CS101'
    assert course.title == 'Intro to CS'
    assert course.academic_year == 2026
    assert course.semester == 1
    assert 'CS101' in str(course)


def test_course_code_not_globally_unique():
    Course.objects.create(code='CS101', academic_year=2026, semester=1)
    Course.objects.create(code='CS101', academic_year=2027, semester=1)
    assert Course.objects.filter(code='CS101').count() == 2


def test_course_membership_creation():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    membership = CourseMembership.objects.create(course=course, user_id=101, role=Role.STUDENT)
    assert membership.user_id == 101
    assert membership.role == Role.STUDENT


def test_course_membership_duplicate_role_rejected():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    CourseMembership.objects.create(course=course, user_id=101, role=Role.STUDENT)
    with pytest.raises(IntegrityError):
        CourseMembership.objects.create(course=course, user_id=101, role=Role.STUDENT)


def test_course_membership_distinct_roles_allowed():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    CourseMembership.objects.create(course=course, user_id=101, role=Role.STUDENT)
    CourseMembership.objects.create(course=course, user_id=101, role=Role.TA)
    assert CourseMembership.objects.filter(course=course, user_id=101).count() == 2


def test_module_section_and_material_cascade():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    section = ModuleSection.objects.create(title='Section 1', course=course)
    material = CourseMaterial.objects.create(
        title='Lecture 1',
        kind=MaterialKind.FILE,
        status=ContentStatus.PUBLISHED,
        section=section,
    )
    assert material.section == section
    section.delete()
    assert CourseMaterial.objects.filter(id=material.id).exists() is False


def test_announcement_author_integer_id():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    announcement = Announcement.objects.create(course=course, author_user_id=202, author_role='instructor', title='Welcome', content='Hello')
    assert announcement.author_user_id == 202


def test_assignment_and_submission_versioning():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    assignment = Assignment.objects.create(course=course, author_user_id=101, title='Assignment 1', points_possible=100)
    submission_v1 = Submission.objects.create(
        assignment=assignment,
        student_user_id=301,
        version=1,
        submission_type=SubmissionType.FILE,
    )
    submission_v2 = Submission.objects.create(
        assignment=assignment,
        student_user_id=301,
        version=2,
        submission_type=SubmissionType.FILE,
    )
    assert submission_v1.version == 1
    assert submission_v2.version == 2
    assert Submission.objects.filter(assignment=assignment, student_user_id=301).count() == 2


def test_grade_one_to_one_and_audit_log():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    assignment = Assignment.objects.create(course=course, author_user_id=101, title='Assignment 1', points_possible=100)
    submission = Submission.objects.create(assignment=assignment, student_user_id=301, submission_type=SubmissionType.FILE)
    grade = Grade.objects.create(
        submission=submission,
        assessor_user_id=401,
        assessor_role='instructor',
        points_awarded=95,
        status=GradeStatus.DRAFT,
    )
    audit_log = GradeAuditLog.objects.create(
        grade=grade,
        assessor_user_id=401,
        action=GradeAction.CREATED,
        new_points=95,
    )
    assert grade.submission == submission
    assert audit_log.grade == grade


def test_contracts_batched_queries():
    course = Course.objects.create(code='CS101', title='Intro to CS', academic_year=2026, semester=1)
    CourseMembership.objects.create(course=course, user_id=101, role=Role.STUDENT)
    assignment = Assignment.objects.create(course=course, author_user_id=201, title='Assignment 1', points_possible=100)

    courses = get_courses([course.id])
    assert course.id in courses
    assert courses[course.id].code == 'CS101'

    user_courses = get_user_courses(user_id=101)
    assert len(user_courses) == 1
    assert user_courses[0].id == course.id

    memberships = get_course_memberships(course_id=course.id)
    assert len(memberships) == 1
    assert memberships[0].user_id == 101

    assignments = get_assignments([assignment.id])
    assert assignment.id in assignments
    assert assignments[assignment.id].title == 'Assignment 1'
