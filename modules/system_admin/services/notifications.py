"""Outbox notifications delivery service for system_admin."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.core.mail import send_mail
from django.utils import timezone

from modules.system_admin.constants import NotificationChannel, NotificationStatus
from modules.system_admin.models import NotificationOutbox

log = logging.getLogger("fusion.system_admin.notifications")


def queue_notification(
    recipient_id: int,
    email: str,
    channel: str,
    template_code: str,
    subject: str,
    body: str,
    context: Optional[Dict[str, Any]] = None,
) -> NotificationOutbox:
    """Queue a notification in the reliable outbox (AFR-SA-068..071B, BR-SA-023)."""
    return NotificationOutbox.objects.create(
        recipient_id=recipient_id,
        recipient_email=email,
        channel=channel,
        template_code=template_code,
        subject=subject,
        body=body,
        status=NotificationStatus.PENDING,
        context_data=context or {},
    )


def deliver_pending_notifications(batch_size: int = 50) -> Dict[str, int]:
    """Drain pending outbox items within the 1-hour SLA (BR-SA-023)."""
    now = timezone.now()
    pending = (
        NotificationOutbox.objects.filter(
            status=NotificationStatus.PENDING,
            scheduled_for__lte=now,
        )
        .order_by("scheduled_for")[:batch_size]
    )

    delivered = 0
    failed = 0

    for item in pending:
        try:
            if item.channel == NotificationChannel.EMAIL and item.recipient_email:
                send_mail(
                    subject=item.subject,
                    message=item.body,
                    from_email=None,  # Uses DEFAULT_FROM_EMAIL
                    recipient_list=[item.recipient_email],
                    fail_silently=False,
                )
            elif item.channel == NotificationChannel.SMS:
                # SMS dispatch stub for critical security alerts (BR-SA-024)
                log.info("system_admin.sms.dispatched recipient=%d subject=%s", item.recipient_id, item.subject)

            item.status = NotificationStatus.SENT
            item.sent_at = timezone.now()
            item.save(update_fields=["status", "sent_at"])
            delivered += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("system_admin.notify.failed id=%d err=%s", item.id, exc)
            item.retry_count += 1
            item.error_message = str(exc)
            if item.retry_count >= 5:
                item.status = NotificationStatus.FAILED
            item.save(update_fields=["status", "retry_count", "error_message"])
            failed += 1

    return {"delivered": delivered, "failed": failed}
