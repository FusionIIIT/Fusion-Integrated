"""Course Assignments write services (CFR-LMS-006, BR-LMS-004, BR-LMS-010)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.courses.domain.assignments import (
    AssignmentCreateDTO,
    AssignmentUpdateDTO,
)
from modules.courses.domain.errors import CourseDomainError
from modules.courses.models import CourseAssignment, CourseWorkspace
from modules.courses.selectors import scoping

log = logging.getLogger("fusion.courses.assignments")


def create_assignment(
    *,
    workspace_id: int,
    principal,
    title: str,
    description: str = "",
    instructions: str = "",
    max_points: Decimal = Decimal("100.00"),
    due_at: datetime | None = None,
    is_published: bool = False,
) -> CourseAssignment:
    """Creates a new course assignment (AFR-LMS-006.1).

    Enforces BR-LMS-004 (TAs cannot author assignments),
    BR-LMS-009 (configuration validation), and BR-LMS-010 (draft before publication).
    """
    dto = AssignmentCreateDTO(
        title=title,
        description=description,
        instructions=instructions,
        max_points=max_points,
        due_at=due_at,
        is_published=is_published,
    )
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        # Check authorization: Only assigned faculty instructors can create assignments (BR-LMS-004)
        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course assignments."
                )
            raise NotFoundError("Course workspace not found.")

        published_at = timezone.now() if is_published else None

        assignment = CourseAssignment.objects.create(
            workspace=workspace,
            title=title.strip(),
            description=description.strip(),
            instructions=instructions.strip(),
            max_points=max_points if max_points is not None else Decimal("100.00"),
            due_at=due_at,
            is_published=is_published,
            published_at=published_at,
            created_by_id=principal.user_id,
        )

        log.info(
            "courses.assignment.created id=%d workspace=%s published=%s due=%s",
            assignment.id,
            workspace.code,
            is_published,
            assignment.due_at,
        )
        return assignment


def update_assignment(
    *,
    workspace_id: int,
    assignment_id: int,
    principal,
    title: str | None = None,
    description: str | None = None,
    instructions: str | None = None,
    max_points: Decimal | None = None,
    due_at: datetime | None = None,
    clear_due_at: bool = False,
    is_published: bool | None = None,
) -> CourseAssignment:
    """Updates an existing course assignment."""
    dto = AssignmentUpdateDTO(
        title=title,
        description=description,
        instructions=instructions,
        max_points=max_points,
        due_at=due_at,
        clear_due_at=clear_due_at,
        is_published=is_published,
    )
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
                    "Only assigned faculty instructors may manage course assignments."
                )
            raise NotFoundError("Course workspace not found.")

        assignment = (
            CourseAssignment.objects.filter(id=assignment_id, workspace=workspace)
            .select_for_update()
            .first()
        )
        if not assignment:
            raise NotFoundError("Course assignment not found.")

        if title is not None:
            assignment.title = title.strip()
        if description is not None:
            assignment.description = description.strip()
        if instructions is not None:
            assignment.instructions = instructions.strip()
        if max_points is not None:
            assignment.max_points = max_points

        if clear_due_at:
            assignment.due_at = None
        elif due_at is not None:
            assignment.due_at = due_at

        if is_published is not None:
            if is_published and not assignment.is_published and not assignment.published_at:
                assignment.published_at = timezone.now()
            assignment.is_published = is_published

        assignment.save()
        log.info(
            "courses.assignment.updated id=%d workspace=%s due=%s",
            assignment.id,
            workspace.code,
            assignment.due_at,
        )
        return assignment


def delete_assignment(
    *,
    workspace_id: int,
    assignment_id: int,
    principal,
) -> None:
    """Deletes an assignment from the course workspace."""
    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        if not scoping.is_course_instructor(workspace, principal):
            membership = scoping.get_workspace_membership(workspace, principal)
            if membership and membership.role in ("ta", "student", "observer"):
                raise PermissionDeniedError(
                    "Only assigned faculty instructors may manage course assignments."
                )
            raise NotFoundError("Course workspace not found.")

        assignment = CourseAssignment.objects.filter(
            id=assignment_id, workspace=workspace
        ).first()
        if not assignment:
            raise NotFoundError("Course assignment not found.")

        asgn_id = assignment.id
        assignment.delete()
        log.info(
            "courses.assignment.deleted id=%d workspace=%s",
            asgn_id,
            workspace.code,
        )
