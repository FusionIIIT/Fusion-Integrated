"""CMS scheduled work. Task inputs are ids and passes are retry safe."""

from celery import shared_task


@shared_task(
    name="complaints.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int | None = None) -> str:
    from modules.complaints.services.notifications import deliver_pending

    report = deliver_pending(limit=limit)
    return str(report)


@shared_task(
    name="complaints.process_sla",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def process_sla(limit: int = 500) -> dict[str, int]:
    from modules.complaints.services.complaints import process_sla as process

    return process(limit=limit)
