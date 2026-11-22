from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.lms.tasks")


@shared_task(
    name="lms.publish_scheduled_content",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def publish_scheduled_content() -> int:
    """Release scheduled course materials and assignments whose release date has arrived."""
    from modules.lms.services.courses import release_scheduled_items

    count = release_scheduled_items()
    if count:
        log.info("lms.scheduled_content.released count=%d", count)
    return count
