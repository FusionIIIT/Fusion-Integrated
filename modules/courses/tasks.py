"""Celery tasks for the Courses / LMS module (AFR-LMS-003.4, BW-LMS-01)."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.courses.tasks")


@shared_task(
    name="courses.publish_scheduled_materials",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def publish_scheduled_materials() -> int:
    """Trigger release of course materials whose schedule time has arrived."""
    from modules.courses.services.materials import publish_scheduled_materials as do_publish

    released_count = do_publish()
    log.info("courses.publish_scheduled_materials task completed: %d released", released_count)
    return released_count

