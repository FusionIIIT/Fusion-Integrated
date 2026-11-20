"""Scheduled PMS automation entry points."""

from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.pms.tasks")


@shared_task(
    name="pms.monitor_deadlines",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def monitor_deadlines() -> dict[str, int]:
    """Process policy-driven deadline alerts, expiry and escalations."""
    from modules.pms.services import monitor_and_process_deadlines

    report = monitor_and_process_deadlines()
    log.info("pms.deadlines.run %s", report)
    return report


@shared_task(
    name="pms.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> int:
    """Drain the PMS notification outbox."""
    from modules.pms.services import send_pending_notifications

    sent = send_pending_notifications(limit=limit or 50)
    log.info("pms.notify.run sent=%d", sent)
    return sent
