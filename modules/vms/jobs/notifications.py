"""Celery task bodies for lane E. Importable before apps are ready; the beat
entries and routes are declared in `jobs/lifecycle.py`. Model-touching imports
live inside the bodies."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.vms.jobs")

_OPTS = {"acks_late": True, "reject_on_worker_lost": True,
         "soft_time_limit": 270, "time_limit": 300}


@shared_task(name="vms.deliver_notifications", **_OPTS)
def deliver_notifications(limit: int = 100) -> str:
    """Drain the notification outbox. No autoretry: rows carry their own backoff."""
    from modules.vms.services import delivery

    report = delivery.deliver_pending(limit=limit)
    log.info("vms.notify.run %s", report)
    return str(report)


@shared_task(name="vms.send_reminders", **_OPTS)
def send_reminders() -> int:
    from modules.vms.services import scheduler_work

    return scheduler_work.send_reminders()


@shared_task(name="vms.expire_pending", **_OPTS)
def expire_pending() -> int:
    from modules.vms.services import scheduler_work

    return scheduler_work.expire_pending()
