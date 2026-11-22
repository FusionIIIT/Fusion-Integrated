"""Celery tasks for scheduled VMS background maintenance."""

from celery import shared_task

from modules.vms.services.scheduled import (
    auto_checkout_overstays,
    expire_pending_requests,
)


@shared_task
def expire_pending_requests_task(timeout_hours: int = 24) -> int:
    """Expire pending requests exceeding approval SLA (UC-037)."""
    return expire_pending_requests(timeout_hours=timeout_hours)


@shared_task
def auto_checkout_overstays_task() -> int:
    """Check out on-site visitors who remained on campus past limit (UC-038)."""
    return auto_checkout_overstays()
