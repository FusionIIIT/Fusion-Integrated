"""Celery tasks for background processing in ELM module."""
try:
    from celery import shared_task
except ImportError:
    # If Celery is not installed or mocked in dev/test environment
    def shared_task(fn):
        return fn

from modules.elm.services.leave_service import process_sla_thresholds


@shared_task
def process_elm_sla_task():
    """Periodic task running SLA threshold reminders and escalations."""
    return process_sla_thresholds()
