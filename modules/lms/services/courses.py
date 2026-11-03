from django.core.exceptions import PermissionDenied
from modules.lms.domain.constants import Role
from modules.lms.models import Course, CourseMembership


def create_course(
    code: str,
    title: str,
    academic_year: int,
    semester: int,
    description: str = "",
    syllabus: str = "",
    schedule: str = "",
) -> Course:
    return Course.objects.create(
        code=code,
        title=title,
        academic_year=academic_year,
        semester=semester,
        description=description,
        syllabus=syllabus,
        schedule=schedule,
        is_active=True,
    )


def add_course_membership(course_id: int, user_id: int, role: str, is_projection: bool = False) -> CourseMembership:
    if role == Role.STUDENT and not is_projection:
        raise PermissionDenied(
            "Direct student registration in LMS is prohibited. Student enrollment must originate from the institutional AcademicAdapter projection."
        )
    membership, created = CourseMembership.objects.get_or_create(
        course_id=course_id,
        user_id=user_id,
        role=role,
        defaults={"is_active": True},
    )
    if not created and not membership.is_active:
        membership.is_active = True
        membership.save(update_fields=["is_active", "updated_at"])
    return membership


def remove_course_membership(course_id: int, user_id: int, role: str) -> bool:
    count = CourseMembership.objects.filter(
        course_id=course_id,
        user_id=user_id,
        role=role,
        is_active=True,
    ).update(is_active=False)
    return count > 0
