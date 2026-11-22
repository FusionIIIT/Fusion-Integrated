"""Scheduled MMS tasks.

Ids only in arguments, never ORM objects. Everything is idempotent, because
`acks_late` means a task can run twice if a worker dies mid-flight.
"""

from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.mms.tasks")


@shared_task(
    name="mms.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    """Drain the MMS notification outbox."""
    from modules.mms.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("mms.notify.run %s", report)
    return str(report)


@shared_task(
    name="mms.default_reject_special_food",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def default_reject_special_food() -> int:
    """Auto-reject special-food requests past their decision period."""
    from modules.mms.services import special_food

    count = special_food.default_reject_undecided()
    log.info("mms.default_reject_special_food rejected=%d", count)
    return count


@shared_task(
    name="mms.default_vacation_response",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def default_vacation_response() -> int:
    """Record default-No for registered students with no survey response."""
    from modules.mms.services import survey

    count = survey.apply_default_no()
    log.info("mms.default_vacation_response defaulted=%d", count)
    return count


@shared_task(
    name="mms.activate_deregistration",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def activate_deregistration() -> int:
    """Make approved deregistrations effective from the next calendar day."""
    from modules.mms.services import deregistration

    count = deregistration.activate_approved()
    log.info("mms.activate_deregistration activated=%d", count)
    return count


@shared_task(
    name="mms.generate_monthly_bills",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def generate_monthly_bills() -> int:
    """Generate monthly bills for the calendar-month cycle."""
    from modules.mms.services import billing

    count = billing.generate_monthly()
    log.info("mms.generate_monthly_bills generated=%d", count)
    return count


@shared_task(
    name="mms.send_vacation_reminder",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def send_vacation_reminder() -> int:
    """Send vacation survey reminder emails (cadence is institution-defined)."""
    from modules.mms.services import survey

    count = survey.send_reminders()
    log.info("mms.send_vacation_reminder sent=%d", count)
    return count
