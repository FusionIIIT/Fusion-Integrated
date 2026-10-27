from celery import shared_task
from django.utils import timezone


@shared_task(name="leave.process_sla_thresholds", acks_late=True)
def process_leave_sla_thresholds():
    from modules.leave.services.sla import process_sla_thresholds
    return process_sla_thresholds()


@shared_task(name="leave.deliver_notifications", acks_late=True)
def deliver_leave_notifications():
    from modules.leave.services.notifications import deliver_pending
    return deliver_pending()


@shared_task(name="leave.run_year_end_processing", acks_late=True)
def run_leave_year_end_processing():
    from modules.leave.services.year_end import run_year_end_processing
    return run_year_end_processing(timezone.localdate().year - 1)
