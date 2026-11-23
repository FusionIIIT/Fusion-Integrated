"""Celery background tasks for LMS."""

from __future__ import annotations

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from modules.lms.domain.constants import AssignmentStatus, MaterialStatus
from modules.lms.models import Assignment, CourseMaterial


@shared_task(name="lms.tasks.process_scheduled_content_release")
def process_scheduled_content_release() -> dict[str, int]:
    """Transitions scheduled materials and assignments to published once release time passes."""
    now = timezone.now()
    with transaction.atomic():
        mat_count = CourseMaterial.objects.filter(
            status=MaterialStatus.SCHEDULED,
            release_date__lte=now,
        ).update(status=MaterialStatus.PUBLISHED)

        asg_count = Assignment.objects.filter(
            status=AssignmentStatus.SCHEDULED,
            release_date__lte=now,
        ).update(status=AssignmentStatus.PUBLISHED)

    return {"materials_released": mat_count, "assignments_released": asg_count}
