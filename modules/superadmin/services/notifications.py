from __future__ import annotations

from typing import Any

from django.utils import timezone

from modules.superadmin.domain.constants import NOTIF_CHANNEL_EMAIL
from modules.superadmin.models.notifications import NotificationOutbox


def queue_notification(
    *,
    recipient_id: int,
    recipient_email: str,
    template_code: str,
    subject: str,
    body: str,
    channel: str = NOTIF_CHANNEL_EMAIL,
    context_data: dict[str, Any] | None = None,
) -> NotificationOutbox:
    # Transactional outbox pattern guaranteeing at-least-once notification delivery
    return NotificationOutbox.objects.create(
        recipient_id=recipient_id,
        recipient_email=recipient_email,
        template_code=template_code,
        subject=subject,
        body=body,
        channel=channel,
        context_data=context_data or {},
        scheduled_for=timezone.now(),
    )
