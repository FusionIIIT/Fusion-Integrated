"""Celery tasks for SPACS background processing."""

from celery import shared_task


@shared_task(name="spacs.check_sla_tasks")
def check_sla_tasks(sla_hours: int = 48) -> int:
    """Escalate pending tasks older than the SLA threshold."""
    from modules.spacs.services import tasks as task_svc

    escalated = task_svc.check_and_escalate_sla_tasks(sla_hours=sla_hours)
    return len(escalated)


@shared_task(name="spacs.close_expired_cycles")
def close_expired_cycles() -> int:
    """Auto-close award cycles that have passed their submission deadline."""
    from django.utils import timezone

    from modules.spacs.models import SpacsAwardCycle

    now = timezone.now()
    expired_cycles = SpacsAwardCycle.objects.filter(
        state="open",
        created_at__lt=now,
    )
    count = 0
    for cycle in expired_cycles:
        cycle.state = "closed"
        cycle.save(update_fields=["state", "updated_at"])
        count += 1
    return count
