import logging

from celery import shared_task

log = logging.getLogger("fusion.spacs.tasks")


@shared_task(
    name="spacs.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    from modules.spacs.services import notifications

    report = notifications.deliver_pending(limit=limit)
    log.info("spacs.notify.run %s", report)
    return str(report)
