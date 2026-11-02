"""Scheduled course-content release (UC-LMS-015)."""
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from modules.lms.models import Assignment, CourseMaterial


def release_scheduled_content_now(*, now=None) -> dict[str, int]:
    now = now or timezone.now()
    with transaction.atomic():
        materials = list(CourseMaterial.objects.select_for_update().filter(
            status="scheduled", release_at__lte=now))
        for row in materials:
            row.status = "published"
            row.published_at = now
            row.updated_at = now
        CourseMaterial.objects.bulk_update(
            materials, ["status", "published_at", "updated_at"])

        assignments = list(Assignment.objects.select_for_update().filter(
            status="scheduled", release_at__lte=now))
        for row in assignments:
            row.status = "available"
            row.updated_at = now
        Assignment.objects.bulk_update(assignments, ["status", "updated_at"])
    return {"materials": len(materials), "assignments": len(assignments)}


@shared_task(name="lms.release_scheduled_content")
def release_scheduled_content() -> dict[str, int]:
    return release_scheduled_content_now()
