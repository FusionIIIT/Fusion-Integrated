"""Scheduled work. Ids only in arguments; every task is idempotent, because
`acks_late` means one can run twice if a worker dies mid-flight."""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.visitor_hostel.tasks")


@shared_task(name="visitor_hostel.deliver_notifications", acks_late=True,
             reject_on_worker_lost=True, soft_time_limit=270, time_limit=300)
def deliver_notifications(limit: int | None = None) -> str:
    from modules.visitor_hostel.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("visitor_hostel.notify.run %s", report)
    return str(report)


@shared_task(name="visitor_hostel.scan_stays", acks_late=True,
             reject_on_worker_lost=True, soft_time_limit=270, time_limit=300)
def scan_stays() -> dict:
    """BR-VH-017 / BR-VH-018."""
    from modules.visitor_hostel.services import stays

    return stays.scan()


@shared_task(name="visitor_hostel.send_stay_reminders", acks_late=True)
def send_stay_reminders() -> dict:
    """AFR-VH-079."""
    from modules.visitor_hostel.services import stays

    return stays.send_reminders()


@shared_task(name="visitor_hostel.close_lapsed_duty", acks_late=True)
def close_lapsed_duty() -> int:
    """BR-VH-047: a time-bound assignment ends on time, not when someone notices."""
    from modules.visitor_hostel.services import duty

    return duty.close_lapsed()
