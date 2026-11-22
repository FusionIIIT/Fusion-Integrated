"""Scheduled MMS work."""

from celery import shared_task


@shared_task(name="mms.apply_vacation_defaults", acks_late=True, reject_on_worker_lost=True)
def apply_vacation_defaults() -> int:
    from modules.mms.services.workflows import apply_vacation_defaults as apply_defaults

    return apply_defaults()
