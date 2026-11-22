from django.db import IntegrityError, transaction

from modules.leave.models import LeaveNotification


def enqueue(*, topic: str, dedupe_key: str, recipient_user_id: int,
            subject: str, body: str) -> LeaveNotification | None:
    try:
        with transaction.atomic():
            return LeaveNotification.objects.create(
                topic=topic, dedupe_key=dedupe_key,
                recipient_user_id=recipient_user_id, subject=subject, body=body,
            )
    except IntegrityError:
        return None
