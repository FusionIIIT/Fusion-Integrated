"""Celery task wrappers for the IAA event-triggered use cases."""
from celery import shared_task


@shared_task(name="iaa.escalate_overdue_approvals", acks_late=True,
             reject_on_worker_lost=True)
def escalate_overdue_approvals():
    from modules.iaa.services.events import escalate_overdue
    return escalate_overdue()


@shared_task(name="iaa.process_automatic_anomalies", acks_late=True,
             reject_on_worker_lost=True)
def process_automatic_anomalies():
    from modules.iaa.services.events import process_automatic_anomalies as process
    return process()
