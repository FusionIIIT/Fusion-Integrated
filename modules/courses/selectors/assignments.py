"""Selectors for Course Assignments with role and course scoping (BR-LMS-001, BR-LMS-004, BR-LMS-010)."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.courses.models import CourseAssignment, CourseWorkspace
from modules.courses.selectors import scoping


def visible_assignments(
    workspace: CourseWorkspace, principal,
) -> QuerySet[CourseAssignment]:
    """Returns assignments in the workspace visible to the requesting actor.

    Faculty instructors see all assignments (published and drafts)
    for courses they instruct.

    Students, TAs, and Observers see ONLY assignments where:
    is_published = True (BR-LMS-010).
    """
    if not principal:
        return CourseAssignment.objects.none()

    membership = scoping.get_workspace_membership(workspace, principal)
    if not membership:
        return CourseAssignment.objects.none()

    qs = CourseAssignment.objects.filter(workspace=workspace)

    # Faculty instructors see all assignments (drafts and published)
    if scoping.is_course_instructor(workspace, principal):
        return qs.order_by("-created_at", "-id")

    # Non-faculty roles (students, TAs, observers): only published assignments
    return qs.filter(is_published=True).order_by("-created_at", "-id")


def get_assignment_for_actor(
    workspace_id: int,
    assignment_id: int,
    principal,
) -> CourseAssignment | None:
    """Retrieves a single assignment scoped strictly to the specified workspace."""
    workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
    if not workspace:
        return None

    return visible_assignments(workspace, principal).filter(id=assignment_id).first()

