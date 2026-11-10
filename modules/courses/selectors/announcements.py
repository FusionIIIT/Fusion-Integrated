"""Selectors for Course Announcements with role and course scoping (BR-LMS-001, BR-LMS-005, BR-LMS-008)."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.courses.models import CourseAnnouncement, CourseWorkspace
from modules.courses.selectors import scoping


def visible_announcements(
    workspace: CourseWorkspace, principal,
) -> QuerySet[CourseAnnouncement]:
    """Returns announcements in the workspace visible to the requesting actor.

    Faculty instructors see all announcements (published and drafts)
    for courses they instruct.

    Students, TAs, and Observers see ONLY announcements where:
    is_published = True (BR-LMS-005, BR-LMS-008).
    """
    if not principal:
        return CourseAnnouncement.objects.none()

    membership = scoping.get_workspace_membership(workspace, principal)
    if not membership:
        return CourseAnnouncement.objects.none()

    qs = CourseAnnouncement.objects.filter(workspace=workspace)

    # Faculty instructors see all announcements (drafts and published)
    if scoping.is_course_instructor(workspace, principal):
        return qs.order_by("-published_at", "-created_at", "-id")

    # Non-faculty roles (students, TAs, observers): only published announcements
    return qs.filter(is_published=True).order_by("-published_at", "-created_at", "-id")


def get_announcement_for_actor(
    workspace_id: int,
    announcement_id: int,
    principal,
) -> CourseAnnouncement | None:
    """Retrieves a single announcement scoped strictly to the specified workspace."""
    workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
    if not workspace:
        return None

    return visible_announcements(workspace, principal).filter(id=announcement_id).first()

