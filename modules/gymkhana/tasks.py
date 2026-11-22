"""Gymkhana scheduled background tasks (Blueprint §3.7)."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from modules.gymkhana.models import Poll

log = logging.getLogger("fusion.gymkhana.tasks")


@shared_task(
    name="gymkhana.close_expired_polls",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def close_expired_polls() -> int:
    """Close active polls past their expiration date (BR-GYM-014)."""
    count = Poll.objects.filter(
        status="active",
        expires_at__lte=timezone.now(),
    ).update(status="expired")
    if count:
        log.info("gymkhana.polls.expired count=%d", count)
    return count


@shared_task(
    name="gymkhana.deliver_notifications",
    acks_late=True,
    soft_time_limit=55,
    time_limit=60,
)
def deliver_notifications(**kwargs) -> str:
    """Execution hook for Gymkhana notification delivery."""
    log.info("gymkhana.deliver_notifications executed %s", kwargs)
    return "delivered"
