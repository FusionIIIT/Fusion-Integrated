"""Scheduled content release processing (UC-LMS-015, BW-LMS-01, BW-LMS-03)."""
from django.utils import timezone
from modules.lms.models import CourseMaterial, Assignment


def process_scheduled_releases() -> dict[str, int]:
    """Find scheduled materials and assignments whose release date has arrived and publish them."""
    now = timezone.now()

    # Process scheduled materials
    materials_updated = CourseMaterial.objects.filter(
        status="scheduled",
        release_date__lte=now,
    ).update(status="published")

    # Process scheduled assignments
    assignments_updated = Assignment.objects.filter(
        status="scheduled",
        release_date__lte=now,
    ).update(status="published")

    return {
        "materials_released": materials_updated,
        "assignments_released": assignments_updated,
    }
