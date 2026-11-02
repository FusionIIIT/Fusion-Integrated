"""Celery background tasks for LMS module."""
from celery import shared_task

from modules.lms.services.materials import release_scheduled_materials


@shared_task(name="lms.release_scheduled_materials")
def release_scheduled_materials_task() -> int:
    """Evaluate and publish scheduled course materials whose release time has arrived.

    Satisfies AFR-LMS-003.4, UC-LMS-015, and BW-LMS-01.
    """
    return release_scheduled_materials()
