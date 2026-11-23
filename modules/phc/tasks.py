from celery import shared_task
from django.db import transaction
from django.utils import timezone

from modules.phc.models import Notification, NotificationOutbox


@shared_task(name="phc.deliver_notifications", acks_late=True)
def deliver_notifications(limit: int = 100) -> int:
    delivered = 0
    with transaction.atomic():
        rows = list(NotificationOutbox.objects.filter(
            delivered_at__isnull=True
        ).order_by("id").select_for_update(skip_locked=True)[:limit])
        now = timezone.now()
        for row in rows:
            state = row.payload.get("state", "updated")
            if row.event_type == "reimbursement_status":
                message = f"Your reimbursement claim status is now {state.replace('_', ' ')}."
            else:
                message = f"Your inventory requisition status is now {state.replace('_', ' ')}."
            Notification.objects.get_or_create(
                outbox=row,
                defaults={
                    "recipient_user_id": row.recipient_user_id,
                    "event_type": row.event_type,
                    "message": message,
                    "target_type": row.payload["target_type"],
                    "target_id": row.payload["target_id"],
                },
            )
            row.delivered_at = now
            row.save(update_fields=["delivered_at", "updated_at"])
            delivered += 1
    return delivered
