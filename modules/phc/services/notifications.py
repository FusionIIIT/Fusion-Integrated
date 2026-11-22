from django.db import transaction
from django.db.utils import IntegrityError

from modules.phc.models import NotificationOutbox


def enqueue(*, event_key: str, recipient_user_id: int, event_type: str,
            payload: dict) -> NotificationOutbox:
    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                event_key=event_key,
                recipient_user_id=recipient_user_id,
                event_type=event_type,
                payload=payload,
            )
    except IntegrityError:
        if NotificationOutbox.objects.filter(event_key=event_key).exists():
            return NotificationOutbox.objects.get(event_key=event_key)
        raise
