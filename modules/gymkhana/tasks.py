from celery import shared_task


@shared_task(
    name="gymkhana.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int = 500) -> dict[str, int]:
    from modules.gymkhana.services.notifications import deliver_pending

    return deliver_pending(limit=limit)
