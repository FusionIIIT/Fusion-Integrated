"""Scheduled work for ELM.

Ids only in arguments, never ORM objects. Everything is
idempotent, because `acks_late` means a task can run
twice if a worker dies mid-flight.
"""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger("fusion.elm.tasks")


@shared_task(
    name="elm.deliver_notifications",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    """Drain the ELM notification outbox (BR-EL-035).

    No autoretry — the rows carry their own attempts and
    backoff, so a failed pass is picked up by the next
    beat rather than re-sending the batch.
    """
    from modules.elm.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("elm.notify.run %s", report)
    return str(report)


@shared_task(
    name="elm.sla_sweep",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def sla_sweep() -> str:
    """One SLA reminder/escalation pass (EL-UC-021).

    Pending tasks only — a completed task's clock has
    stopped, so it is never reminded or escalated.
    """
    from modules.elm.services import sla

    report = sla.sweep()
    log.info("elm.sla.sweep %s", report)
    return str(report)
