"""Course assignment selectors."""

from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.utils import timezone

from modules.lms.domain.constants import AssignmentStatus
from modules.lms.models import Assignment
from modules.lms.selectors.scoping import (
    has_course_access,
    is_course_instructor,
    is_course_ta,
)


def list_assignments(course_id: int, principal: Any) -> list[Assignment]:
    if not has_course_access(course_id, principal):
        return []

    is_staff = is_course_instructor(course_id, principal) or is_course_ta(course_id, principal)
    qs = Assignment.objects.filter(course_id=course_id)
    if is_staff:
        return list(qs.exclude(status=AssignmentStatus.ARCHIVED).order_by("due_date"))

    now = timezone.now()
    return list(
        qs.filter(status__in=[AssignmentStatus.PUBLISHED, AssignmentStatus.CLOSED])
        .filter(Q(release_date__isnull=True) | Q(release_date__lte=now))
        .order_by("due_date")
    )


def get_assignment_detail(assignment_id: int, principal: Any) -> Assignment | None:
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment or not has_course_access(assignment.course_id, principal):
        return None

    is_staff = is_course_instructor(assignment.course_id, principal) or is_course_ta(
        assignment.course_id, principal
    )
    if is_staff:
        return assignment

    now = timezone.now()
    if assignment.status in (AssignmentStatus.PUBLISHED, AssignmentStatus.CLOSED) and (
        assignment.release_date is None or assignment.release_date <= now
    ):
        return assignment
    return None
