"""Transactional Course Workspace writes."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.lms.domain.entities import CourseRole, validate_course_details
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import Course, CourseMembership
from modules.lms.services.authz import require

P_MANAGE = "lms.course.manage"


@transaction.atomic
def update_course_workspace(
    *,
    actor,
    course_code: str,
    title: str | None = None,
    description: str | None = None,
    syllabus: str | None = None,
    schedule: str | None = None,
    status: str | None = None,
) -> Course:
    """Configure or edit course workspace details.

    Strictly restricted to Faculty assigned to this course (AFR-LMS-002.1, AFR-LMS-002.2).
    TAs, Students, and Observers are explicitly prevented from modifying course structure/details
    (AFR-LMS-014.5, AFR-LMS-015.4, BR-LMS-003, BR-LMS-004).
    """
    require(actor, P_MANAGE)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can edit its workspace details."
        )

    course = membership.course

    new_title = title.strip() if title is not None else course.title
    new_status = status.strip() if status is not None else course.status

    try:
        validate_course_details(title=new_title, status=new_status)
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="lms_validation_failed") from exc

    update_fields = ["updated_at"]
    if title is not None:
        course.title = new_title
        update_fields.append("title")
    if description is not None:
        course.description = description.strip()
        update_fields.append("description")
    if syllabus is not None:
        course.syllabus = syllabus.strip()
        update_fields.append("syllabus")
    if schedule is not None:
        course.schedule = schedule.strip()
        update_fields.append("schedule")
    if status is not None:
        course.status = new_status
        update_fields.append("status")

    course.save(update_fields=update_fields)
    return course
