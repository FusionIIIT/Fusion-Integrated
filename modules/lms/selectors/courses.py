from django.db.models import QuerySet
from modules.lms.models import Course, CourseMembership


def get_user_courses(user_id: int) -> QuerySet:
    """Returns distinct active courses where the user has an active membership."""
    return Course.objects.filter(
        memberships__user_id=user_id,
        memberships__is_active=True,
        is_active=True,
    ).distinct()


def get_course_by_id(course_id: int) -> Course | None:
    """Returns a course by ID or None."""
    return Course.objects.filter(id=course_id).first()


def get_course_memberships(course_id: int) -> QuerySet:
    """Returns active memberships for the course."""
    return CourseMembership.objects.filter(
        course_id=course_id,
        is_active=True,
    )


def get_user_membership(course_id: int, user_id: int) -> CourseMembership | None:
    """Returns the user's active membership in the course or None."""
    return CourseMembership.objects.filter(
        course_id=course_id,
        user_id=user_id,
        is_active=True,
    ).first()
