import logging

from celery import shared_task

log = logging.getLogger("fusion.complaints.tasks")


@shared_task(name="complaints.deliver_notifications", acks_late=True,
             reject_on_worker_lost=True, soft_time_limit=270, time_limit=300)
def deliver_notifications(limit=None):
    from modules.complaints.services import deliver_pending

    report = deliver_pending(limit=limit or 100)
    log.info("complaints.notify.run %s", report)
    return report
