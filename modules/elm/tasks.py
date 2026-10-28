"""Celery entry points for ELM's scheduled notification work."""
from celery import shared_task


@shared_task(
    name="elm.process_sla_thresholds",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def process_sla_thresholds() -> str:
    from modules.elm.services.sla import process_sla_thresholds as process

    return str(process())


@shared_task(
    name="elm.deliver_notifications",
    acks_late=True, reject_on_worker_lost=True,
    soft_time_limit=270, time_limit=300,
)
def deliver_notifications() -> str:
    from modules.elm.services.notifications import deliver_pending

    return str(deliver_pending())
