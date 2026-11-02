from datetime import timedelta
import pytest
from django.utils import timezone
from modules.lms.domain.constants import (
    ContentStatus,
    GradeAction,
    GradeStatus,
    MaterialKind,
    Role,
    SubmissionType,
)
from modules.lms.models import (
    Announcement,
    Assignment,
    Course,
    CourseMaterial,
    CourseMembership,
    Grade,
    GradeAuditLog,
    ModuleSection,
    Submission,
)
from modules.lms.selectors import (
    get_announcements_for_course,
    get_assignment_by_id,
    get_assignments_for_course,
    get_course_by_id,
    get_course_memberships,
    get_grade_audit_logs,
    get_grade_for_submission,
    get_grading_queue,
    get_latest_student_submission,
    get_materials_for_section,
    get_sections_for_course,
    get_student_submissions,
    get_user_courses,
    get_user_membership,
)


@pytest.fixture
def test_course(db):
    return Course.objects.create(
        code="CS601",
        title="Distributed Systems",
        academic_year=2026,
        semester=1,
    )


@pytest.mark.django_db
def test_course_selectors(test_course):
    CourseMembership.objects.create(
        course=test_course,
        user_id=101,
        role=Role.STUDENT,
        is_active=True,
    )
    CourseMembership.objects.create(
        course=test_course,
        user_id=102,
        role=Role.INSTRUCTOR,
        is_active=False,
    )

    user_courses = get_user_courses(101)
    assert user_courses.count() == 1
    assert user_courses.first().id == test_course.id

    assert get_user_courses(102).count() == 0  # Inactive membership excluded

    assert get_course_by_id(test_course.id) == test_course
    assert get_course_by_id(99999) is None

    memberships = get_course_memberships(test_course.id)
    assert memberships.count() == 1
    assert memberships.first().user_id == 101

    membership = get_user_membership(test_course.id, 101)
    assert membership is not None
    assert membership.role == Role.STUDENT


@pytest.mark.django_db
def test_content_selectors_visibility(test_course):
    section1 = ModuleSection.objects.create(course=test_course, title="Week 1", order=1)
    section2 = ModuleSection.objects.create(course=test_course, title="Week 2", order=2)

    sections = get_sections_for_course(test_course.id)
    assert list(sections.values_list("id", flat=True)) == [section1.id, section2.id]

    now = timezone.now()
    # Published material (visible to all)
    mat_pub = CourseMaterial.objects.create(
        section=section1,
        title="Intro Slides",
        kind=MaterialKind.FILE,
        status=ContentStatus.PUBLISHED,
        release_date=now - timedelta(days=1),
    )
    # Draft material (visible to staff only)
    CourseMaterial.objects.create(
        section=section1,
        title="Draft Notes",
        kind=MaterialKind.NOTE,
        status=ContentStatus.DRAFT,
    )
    # Embargoed material (visible to staff only)
    CourseMaterial.objects.create(
        section=section1,
        title="Future Lab",
        kind=MaterialKind.FILE,
        status=ContentStatus.PUBLISHED,
        release_date=now + timedelta(days=2),
    )

    student_mats = get_materials_for_section(section1.id, is_staff=False)
    assert student_mats.count() == 1
    assert student_mats.first().id == mat_pub.id

    staff_mats = get_materials_for_section(section1.id, is_staff=True)
    assert staff_mats.count() == 3

    # Announcements
    a1 = Announcement.objects.create(
        course=test_course,
        author_user_id=1,
        author_role=Role.INSTRUCTOR,
        title="General Notice",
        content="Welcome to the course",
    )
    announcements = get_announcements_for_course(test_course.id)
    assert announcements.count() == 1
    assert announcements.first().id == a1.id


@pytest.mark.django_db
def test_assignment_and_grade_selectors(test_course):
    now = timezone.now()
    asg_pub = Assignment.objects.create(
        course=test_course,
        author_user_id=1,
        title="Homework 1",
        status=ContentStatus.PUBLISHED,
        release_date=now - timedelta(days=1),
    )
    Assignment.objects.create(
        course=test_course,
        author_user_id=1,
        title="Midterm",
        status=ContentStatus.DRAFT,
    )

    assert get_assignments_for_course(test_course.id, is_staff=False).count() == 1
    assert get_assignments_for_course(test_course.id, is_staff=True).count() == 2
    assert get_assignment_by_id(asg_pub.id) == asg_pub

    sub1 = Submission.objects.create(
        assignment=asg_pub,
        student_user_id=201,
        version=1,
        submission_type=SubmissionType.FILE,
    )
    sub2 = Submission.objects.create(
        assignment=asg_pub,
        student_user_id=201,
        version=2,
        submission_type=SubmissionType.FILE,
    )

    submissions = get_student_submissions(asg_pub.id, 201)
    assert submissions.count() == 2
    assert get_latest_student_submission(asg_pub.id, 201).id == sub2.id
    assert get_grading_queue(asg_pub.id).count() == 2

    grade = Grade.objects.create(
        submission=sub2,
        assessor_user_id=1,
        assessor_role=Role.TA,
        points_awarded=90,
        status=GradeStatus.DRAFT,
    )
    # Draft grade hidden from student, visible to staff
    assert get_grade_for_submission(sub2.id, is_staff=False) is None
    assert get_grade_for_submission(sub2.id, is_staff=True) == grade

    grade.status = GradeStatus.RELEASED
    grade.save()
    assert get_grade_for_submission(sub2.id, is_staff=False) == grade

    GradeAuditLog.objects.create(
        grade=grade,
        assessor_user_id=1,
        action=GradeAction.RELEASED,
        new_points=90,
        reason="Grade released",
    )
    logs = get_grade_audit_logs(grade.id)
    assert logs.count() == 1
