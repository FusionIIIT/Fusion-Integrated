"""Transactional outbox for ELM email notifications."""
import logging

from django.db import IntegrityError, transaction

from modules.directory.models import UserRef
from modules.elm.models import LeaveNotificationOutbox

log = logging.getLogger("fusion.elm.notify")


def enqueue(*, topic: str, dedupe_key: str, recipient_user_id: int,
            subject: str, body: str) -> LeaveNotificationOutbox | None:
    email = UserRef.objects.filter(user_id=recipient_user_id).values_list(
        "email", flat=True).first() or ""
    try:
        with transaction.atomic():
            return LeaveNotificationOutbox.objects.create(
                topic=topic,
                dedupe_key=dedupe_key,
                recipient_user_id=recipient_user_id,
                recipient_email=email,
                subject=subject,
                body=body,
            )
    except IntegrityError:
        log.debug("elm.notify.duplicate key=%s", dedupe_key)
        return None
