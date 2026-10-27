from django.db import transaction
from .models import LeaveNotificationOutbox

class LeaveNotificationOutboxService:

    @staticmethod
    def enqueue(recipient_user_id: int, topic: str, dedupe_key: str, subject: str, body: str) -> LeaveNotificationOutbox:
        with transaction.atomic():
            outbox, created = LeaveNotificationOutbox.objects.get_or_create(dedupe_key=dedupe_key)
            if created or outbox.status != 'delivered':
                outbox.recipient_user_id = recipient_user_id
                outbox.topic = topic
                outbox.subject = subject
                outbox.body = body
                outbox.save()
        return outbox

    @staticmethod
    def deliver_outbox(limit: int = 50) -> int:
        with transaction.atomic():
            outboxes = LeaveNotificationOutbox.objects.filter(status='pending').order_by('created_at')[:limit]
            count_delivered = outboxes.update(status='delivered')
        return count_delivered