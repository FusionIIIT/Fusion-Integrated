"""Course Announcements write services (CFR-LMS-005, BR-LMS-004, BR-LMS-007)."""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.courses.domain.announcements import (
    AnnouncementCreateDTO,
    AnnouncementUpdateDTO,
)
from modules.courses.domain.errors import CourseDomainError
from modules.courses.models import CourseAnnouncement, CourseWorkspace
from modules.courses.selectors import scoping

log = logging.getLogger("fusion.courses.announcements")


def create_announcement(
    *,
    workspace_id: int,
    principal,
    title: str,
    body: str,
    is_published: bool = True,
) -> CourseAnnouncement:
    """Creates a new course announcement (AFR-LMS-005.1).

    Enforces BR-LMS-004 (TAs cannot author announcements),
    BR-LMS-007 (Faculty authoring authority), and BR-LMS-008 (timestamping).
    """
    dto = AnnouncementCreateDTO(title=title, body=body, is_published=is_published)
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        # Check authorization: Only assigned faculty instructors can create announcements (BR-LMS-004)
        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course announcements."
                )
            raise NotFoundError("Course workspace not found.")

        published_at = timezone.now() if is_published else None

        announcement = CourseAnnouncement.objects.create(
            workspace=workspace,
            title=title.strip(),
            body=body.strip(),
            is_published=is_published,
            published_at=published_at,
            created_by_id=principal.user_id,
        )

        log.info(
            "courses.announcement.created id=%d workspace=%s published=%s",
            announcement.id,
            workspace.code,
            is_published,
        )
        return announcement


def update_announcement(
    *,
    workspace_id: int,
    announcement_id: int,
    principal,
    title: str | None = None,
    body: str | None = None,
    is_published: bool | None = None,
) -> CourseAnnouncement:
    """Updates an existing course announcement."""
    dto = AnnouncementUpdateDTO(title=title, body=body, is_published=is_published)
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course announcements."
                )
            raise NotFoundError("Course workspace not found.")

        announcement = (
            CourseAnnouncement.objects.filter(id=announcement_id, workspace=workspace)
            .select_for_update()
            .first()
        )
        if not announcement:
            raise NotFoundError("Course announcement not found.")

        if title is not None:
            announcement.title = title.strip()
        if body is not None:
            announcement.body = body.strip()

        if is_published is not None:
            if is_published and not announcement.is_published and not announcement.published_at:
                announcement.published_at = timezone.now()
            announcement.is_published = is_published

        announcement.save()
        log.info(
            "courses.announcement.updated id=%d workspace=%s",
            announcement.id,
            workspace.code,
        )
        return announcement


def delete_announcement(
    *,
    workspace_id: int,
    announcement_id: int,
    principal,
) -> None:
    """Deletes an announcement from the course workspace."""
    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course announcements."
                )
            raise NotFoundError("Course workspace not found.")

        announcement = CourseAnnouncement.objects.filter(
            id=announcement_id, workspace=workspace
        ).first()
        if not announcement:
            raise NotFoundError("Course announcement not found.")

        ann_id = announcement.id
        announcement.delete()
        log.info(
            "courses.announcement.deleted id=%d workspace=%s",
            ann_id,
            workspace.code,
        )

