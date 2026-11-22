"""Workspace write operations and configuration services (CFR-LMS-002)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.courses.domain.entities import WorkspaceUpdateDTO
from modules.courses.domain.errors import CourseDomainError
from modules.courses.models import CourseWorkspace
from modules.courses.selectors import scoping


def update_workspace(
    *,
    workspace_id: int,
    principal,
    title: str | None = None,
    description: str | None = None,
    syllabus: str | None = None,
    schedule: str | None = None,
    is_published: bool | None = None,
    allow_ta_announcements: bool | None = None,
) -> CourseWorkspace:
    """Updates course workspace details and configuration.

    Only assigned faculty instructors for the course may update details
    (AFR-LMS-002.1, AFR-LMS-002.2, BR-LMS-004).
    """
    dto = WorkspaceUpdateDTO(
        title=title,
        description=description,
        syllabus=syllabus,
        schedule=schedule,
        is_published=is_published,
        allow_ta_announcements=allow_ta_announcements,
    )
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = (
            CourseWorkspace.objects.filter(id=workspace_id)
            .select_for_update()
            .first()
        )
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        # Access check: Must be an assigned faculty instructor
        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may configure or update "
                    "course workspace details."
                )
            raise NotFoundError("Course workspace not found.")

        if title is not None:
            workspace.title = title.strip()
        if description is not None:
            workspace.description = description
        if syllabus is not None:
            workspace.syllabus = syllabus
        if schedule is not None:
            workspace.schedule = schedule
        if is_published is not None:
            workspace.is_published = is_published
        if allow_ta_announcements is not None:
            workspace.allow_ta_announcements = allow_ta_announcements

        workspace.save()
        return workspace
