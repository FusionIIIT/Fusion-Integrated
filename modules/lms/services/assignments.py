"""Assignment service operations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from modules.lms.domain.constants import AssignmentStatus
from modules.lms.domain.state_machine import AssignmentFSM
from modules.lms.domain.validators import validate_assignment_config
from modules.lms.models import Assignment
from modules.lms.selectors.scoping import is_course_instructor


def create_assignment(
    course_id: int,
    title: str,
    instructions: str,
    points_possible: Decimal | float | int,
    submission_type: str,
    due_date: datetime,
    release_date: datetime | None,
    principal: Any,
) -> Assignment:
    """Creates a new assignment in DRAFT state (CFR-LMS-006, BR-LMS-010)."""
    if not is_course_instructor(course_id, principal):
        raise PermissionDenied("Only assigned instructors may author assignments.")

    validate_assignment_config(
        title=title,
        instructions=instructions,
        points_possible=points_possible,
        submission_type=submission_type,
        due_date=due_date,
        release_date=release_date,
    )

    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None) or 0
    return Assignment.objects.create(
        course_id=course_id,
        title=title,
        instructions=instructions,
        points_possible=Decimal(str(points_possible)),
        submission_type=submission_type,
        due_date=due_date,
        release_date=release_date,
        status=AssignmentStatus.DRAFT,
        created_by=user_id,
    )


def update_assignment(
    assignment_id: int,
    title: str,
    instructions: str,
    points_possible: Decimal | float | int,
    submission_type: str,
    due_date: datetime,
    release_date: datetime | None,
    principal: Any,
) -> Assignment:
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment or not is_course_instructor(assignment.course_id, principal):
        raise PermissionDenied("Only assigned instructors may edit assignments.")

    validate_assignment_config(
        title=title,
        instructions=instructions,
        points_possible=points_possible,
        submission_type=submission_type,
        due_date=due_date,
        release_date=release_date,
    )

    assignment.title = title
    assignment.instructions = instructions
    assignment.points_possible = Decimal(str(points_possible))
    assignment.submission_type = submission_type
    assignment.due_date = due_date
    assignment.release_date = release_date
    assignment.save()
    return assignment


def publish_assignment(
    assignment_id: int,
    release_date: datetime | None,
    principal: Any,
) -> Assignment:
    """Publishes an assignment immediately or sets future scheduled release (CFR-LMS-007)."""
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment or not is_course_instructor(assignment.course_id, principal):
        raise PermissionDenied("Only assigned instructors may publish assignments.")

    if release_date is not None:
        assignment.release_date = release_date

    now = timezone.now()
    new_status = AssignmentFSM.publish(
        current_status=assignment.status,
        release_date=assignment.release_date,
        now=now,
    )
    assignment.status = new_status
    assignment.save(update_fields=["status", "release_date", "updated_at"])
    return assignment


def delete_assignment(assignment_id: int, principal: Any) -> None:
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment:
        return
    if not is_course_instructor(assignment.course_id, principal):
        raise PermissionDenied("Only assigned instructors may delete assignments.")
    assignment.delete()
