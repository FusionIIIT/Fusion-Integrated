from __future__ import annotations

from dataclasses import asdict

from core.api.exceptions import NotFoundError, PermissionDeniedError
from modules.lms.integrations.registration import (
    CourseAccess,
)
from modules.lms.integrations.registration import (
    course_for as source_course_for,
)
from modules.lms.integrations.registration import (
    courses_for as source_courses_for,
)
from modules.lms.models import CourseWorkspace


def _workspace(ref: CourseAccess) -> CourseWorkspace:
    course, _ = CourseWorkspace.objects.update_or_create(
        source_course_id=ref.course_id,
        defaults={"course_code": ref.code, "title": ref.title},
    )
    return course


def _course_data(ref: CourseAccess, course: CourseWorkspace) -> dict:
    return {
        "id": course.pk,
        "source_course_id": ref.course_id,
        "code": ref.code,
        "title": ref.title,
        "role": ref.role,
        "instructors": [asdict(p) for p in ref.instructors],
        "teaching_assistants": [asdict(p) for p in ref.teaching_assistants],
        "may_announce": ref.may_announce,
        "may_grade": ref.may_grade,
        "syllabus": course.syllabus,
        "schedule": course.schedule,
    }


def visible_courses(actor) -> list[dict]:
    refs = source_courses_for(actor.user_id)
    return [_course_data(ref, _workspace(ref)) for ref in refs]


def course_context(actor, source_course_id: str) -> tuple[CourseAccess, CourseWorkspace]:
    ref = source_course_for(actor.user_id, source_course_id)
    if ref is None:
        raise NotFoundError("No such course workspace.")
    return ref, _workspace(ref)


def require_role(ref: CourseAccess, *roles: str) -> None:
    if ref.role not in roles:
        raise PermissionDeniedError("This action is not available for your course role.")


def allow_ta(ref: CourseAccess, capability: str) -> None:
    """TA permissions remain owned by the provider while the PS policy is open."""
    if ref.role != "teaching_assistant":
        return
    allowed = ref.may_announce if capability == "announce" else ref.may_grade
    if not allowed:
        raise PermissionDeniedError(
            "This TA capability is not enabled for the course.",
            code="course_capability_denied")
