from __future__ import annotations

from celery import shared_task

from modules.superadmin.models.notifications import NotificationOutbox
from modules.superadmin.services.archival import expire_reversibility_sweep
from modules.superadmin.services.purge import expire_purge_requests_sweep


@shared_task(name="modules.superadmin.tasks.expire_reversibility_window_task")
def expire_reversibility_window_task() -> int:
    # Daily sweep finalizing permanently non-restorable archived users
    return expire_reversibility_sweep()


@shared_task(name="modules.superadmin.tasks.expire_pending_purge_requests_task")
def expire_pending_purge_requests_task() -> int:
    # Periodic sweep expiring stale unapproved purge requests
    return expire_purge_requests_sweep()


@shared_task(name="modules.superadmin.tasks.drain_notification_outbox_task")
def drain_notification_outbox_task() -> int:
    # Simulates draining outbox notifications to external channel
    count = 0
    pending = NotificationOutbox.objects.filter(status="pending")[:100]
    for n in pending:
        n.status = "sent"
        n.save(update_fields=["status", "updated_at"])
        count += 1
    return count
