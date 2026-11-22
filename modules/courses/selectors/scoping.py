"""Scope filters for Course Workspace access control (BR-LMS-001, AFR-LMS-001.3)."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.courses.models import CourseMembership, CourseWorkspace


def visible_workspaces(principal) -> QuerySet[CourseWorkspace]:
    """Returns only course workspaces the caller is enrolled in or assigned to."""
    if not principal:
        return CourseWorkspace.objects.none()

    member_workspace_ids = CourseMembership.objects.filter(
        user_id=principal.user_id,
    ).values_list("workspace_id", flat=True)

    return CourseWorkspace.objects.filter(
        id__in=member_workspace_ids,
        is_published=True,
    ).order_by("code")


def get_workspace_membership(
    workspace: CourseWorkspace, principal,
) -> CourseMembership | None:
    """Returns the membership record for the principal in this workspace."""
    if not principal:
        return None
    return CourseMembership.objects.filter(
        workspace=workspace,
        user_id=principal.user_id,
    ).first()


def is_course_instructor(workspace: CourseWorkspace, principal) -> bool:
    """True if caller is an assigned faculty instructor for this course (AFR-LMS-002.1)."""
    if not principal:
        return False
    return CourseMembership.objects.filter(
        workspace=workspace,
        user_id=principal.user_id,
        role="instructor",
    ).exists()


def get_workspace_personnel_ids(
    workspace: CourseWorkspace,
) -> tuple[list[int], list[int]]:
    """Returns (instructor_user_ids, ta_user_ids) for the workspace."""
    instructors = list(
        CourseMembership.objects.filter(
            workspace=workspace,
            role="instructor",
        ).values_list("user_id", flat=True)
    )
    tas = list(
        CourseMembership.objects.filter(
            workspace=workspace,
            role="ta",
        ).values_list("user_id", flat=True)
    )
    return instructors, tas
