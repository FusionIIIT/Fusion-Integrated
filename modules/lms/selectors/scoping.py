"""Scoping selectors for LMS (Course Management).

Queryset narrowing so out-of-scope rows return 404, never 403.
"""

from django.db.models import QuerySet
from django.http import Http404

from modules.lms.domain.entities import CourseRole
from modules.lms.models import CourseWorkspace, StudentSubmission


def scope_courses_for_user(user_id: int) -> QuerySet[CourseWorkspace]:
    """Return only courses where user has an active membership (BR-LMS-001, BR-LMS-002)."""
    return (
        CourseWorkspace.objects.filter(
            memberships__user_id=user_id,
            is_active=True,
        )
        .distinct()
        .order_by("course_code")
    )


def get_visible_course_or_404(course_id: int, user_id: int) -> CourseWorkspace:
    """Return course if visible to user; raises Http404 otherwise."""
    course = scope_courses_for_user(user_id).filter(id=course_id).first()
    if not course:
        raise Http404("Course not found or access denied.")
    return course


def scope_submissions_for_user(
    assignment_id: int,
    user_id: int,
    user_role: str,
) -> QuerySet[StudentSubmission]:
    """Return submissions scoped by user role: students only see their own (BR-LMS-014)."""
    qs = StudentSubmission.objects.filter(assignment_id=assignment_id).select_related("grade")
    if user_role == CourseRole.STUDENT.value:
        qs = qs.filter(student_user_id=user_id)
    elif user_role == CourseRole.OBSERVER.value:
        return StudentSubmission.objects.none()
    return qs.order_by("-submitted_at")
