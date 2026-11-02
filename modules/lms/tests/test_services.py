"""Integration tests for LMS Course Workspace and Materials services."""
from datetime import UTC, datetime, timedelta

import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.lms.domain.entities import (
    CourseRole,
    CourseStatus,
    MaterialStatus,
    MaterialType,
    SectionType,
)
from modules.lms.models import Course, CourseMaterial, CourseMembership
from modules.lms.services import courses as course_service
from modules.lms.services import materials as material_service


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


@pytest.mark.django_db
def test_faculty_can_create_link_and_note_material():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(
        9001, "faculty", ("lms.course.view", "lms.material.manage")
    )

    mat_note = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="Lecture 1 Overview",
        section_title="Module 1: Relational Model",
        material_type=MaterialType.NOTE,
        section_type=SectionType.MODULE,
        status=MaterialStatus.PUBLISHED,
        content="Key takeaways: Schema vs Instance, DDL, DML.",
    )
    assert mat_note.id is not None
    assert mat_note.material_type == MaterialType.NOTE
    assert mat_note.status == MaterialStatus.PUBLISHED

    mat_link = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="PostgreSQL Manual",
        section_title="Module 1: Relational Model",
        material_type=MaterialType.LINK,
        link_url="https://www.postgresql.org/docs/",
    )
    assert mat_link.id is not None
    assert mat_link.link_url == "https://www.postgresql.org/docs/"


@pytest.mark.django_db
def test_faculty_can_create_scheduled_material():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(
        9001, "faculty", ("lms.course.view", "lms.material.manage")
    )

    future_release = datetime.now(UTC) + timedelta(days=7)
    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="Midterm Review Sheet",
        section_title="Week 6: Midterm Exam Prep",
        section_type=SectionType.WEEK,
        material_type=MaterialType.NOTE,
        status=MaterialStatus.SCHEDULED,
        release_at=future_release,
        content="Midterm study guide and formula sheet.",
    )
    assert mat.status == MaterialStatus.SCHEDULED
    assert mat.release_at == future_release


@pytest.mark.django_db
def test_ta_cannot_create_or_modify_materials():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=2001, role=CourseRole.TA)

    ta = make_principal(2001, "staff", ("lms.course.view", "lms.material.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        material_service.create_course_material(
            actor=ta,
            course_code="CS301",
            title="TA Note",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            content="TA lab guide",
        )


@pytest.mark.django_db
def test_student_and_observer_cannot_create_materials():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=1001, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=3001, role=CourseRole.OBSERVER)

    student = make_principal(1001, "student", ("lms.course.view", "lms.material.manage"))
    observer = make_principal(3001, "staff", ("lms.course.view", "lms.material.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        material_service.create_course_material(
            actor=student,
            course_code="CS301",
            title="Student upload",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            content="Text",
        )

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        material_service.create_course_material(
            actor=observer,
            course_code="CS301",
            title="Observer upload",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            content="Text",
        )


@pytest.mark.django_db
def test_faculty_can_update_and_delete_material():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(
        9001, "faculty", ("lms.course.view", "lms.material.manage")
    )

    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="Draft Chapter",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.DRAFT,
        content="Draft text",
    )

    updated = material_service.update_course_material(
        actor=faculty,
        course_code="CS301",
        material_id=mat.id,
        title="Final Chapter 1 Notes",
        status=MaterialStatus.PUBLISHED,
        content="Polished text ready for students.",
    )
    assert updated.title == "Final Chapter 1 Notes"
    assert updated.status == MaterialStatus.PUBLISHED

    material_service.delete_course_material(
        actor=faculty,
        course_code="CS301",
        material_id=mat.id,
    )
    assert not CourseMaterial.objects.filter(id=mat.id).exists()


@pytest.mark.django_db
def test_release_scheduled_materials_transition():
    course = Course.objects.create(code="CS301", title="Database Systems")

    past_release = datetime.now(UTC) - timedelta(hours=2)
    future_release = datetime.now(UTC) + timedelta(days=5)

    m1 = CourseMaterial.objects.create(
        course=course,
        title="Scheduled Due for Release",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.SCHEDULED,
        release_at=past_release,
        content="Now active",
        created_by_user_id=9001,
    )
    m2 = CourseMaterial.objects.create(
        course=course,
        title="Still Future Material",
        section_title="Module 2",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.SCHEDULED,
        release_at=future_release,
        content="Not yet",
        created_by_user_id=9001,
    )

    count = material_service.release_scheduled_materials()
    assert count == 1

    m1.refresh_from_db()
    m2.refresh_from_db()
    assert m1.status == MaterialStatus.PUBLISHED
    assert m2.status == MaterialStatus.SCHEDULED

