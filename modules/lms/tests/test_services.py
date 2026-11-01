"""Integration tests for LMS Course Workspace services."""
import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.lms.domain.entities import CourseRole, CourseStatus
from modules.lms.models import Course, CourseMembership
from modules.lms.services import courses as course_service


def make_principal(user_id: int, role: str, permissions: tuple[str, ...]) -> Principal:
    from conftest import make_principal as _mp
    return _mp(
        user_id=user_id,
        kind=role,
        roles=(role,),
        active_role=role,
        permissions=permissions,
        modules=("lms",),
    )


@pytest.mark.django_db
def test_faculty_can_update_assigned_course_details():
    course = Course.objects.create(
        code="CS301",
        title="Database Systems",
        description="Core DBMS",
        syllabus="Initial syllabus",
        schedule="Mon 10:00",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(9001, "faculty", ("lms.course.view", "lms.course.manage"))

    updated = course_service.update_course_workspace(
        actor=faculty,
        course_code="CS301",
        syllabus="Updated detailed syllabus: Relational algebra, SQL, Normalization.",
        schedule="Mon/Wed 10:00-11:30",
    )

    assert updated.syllabus == "Updated detailed syllabus: Relational algebra, SQL, Normalization."
    assert updated.schedule == "Mon/Wed 10:00-11:30"
    assert updated.title == "Database Systems"


@pytest.mark.django_db
def test_unassigned_faculty_cannot_update_course():
    Course.objects.create(code="CS301", title="Database Systems")
    # Faculty 9002 has manage permission, but is NOT assigned to CS301
    faculty_unassigned = make_principal(9002, "faculty", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(NotFoundError):
        course_service.update_course_workspace(
            actor=faculty_unassigned,
            course_code="CS301",
            syllabus="Sneaky syllabus",
        )


@pytest.mark.django_db
def test_ta_cannot_update_course_details():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=2001, role=CourseRole.TA)

    ta = make_principal(2001, "staff", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        course_service.update_course_workspace(
            actor=ta,
            course_code="CS301",
            syllabus="TA syllabus edit attempt",
        )


@pytest.mark.django_db
def test_observer_cannot_update_course_details():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=3001, role=CourseRole.OBSERVER)

    observer = make_principal(3001, "staff", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        course_service.update_course_workspace(
            actor=observer,
            course_code="CS301",
            syllabus="Observer edit attempt",
        )


@pytest.mark.django_db
def test_student_cannot_update_course_details():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=1001, role=CourseRole.STUDENT)

    student = make_principal(1001, "student", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        course_service.update_course_workspace(
            actor=student,
            course_code="CS301",
            syllabus="Student edit attempt",
        )


@pytest.mark.django_db
def test_empty_title_update_rejected():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(9001, "faculty", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(ConflictError, match="title cannot be empty"):
        course_service.update_course_workspace(
            actor=faculty,
            course_code="CS301",
            title="   ",
        )
