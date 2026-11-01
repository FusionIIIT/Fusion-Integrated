"""PMS Notification service (CFR-PMS-023, BR-PMS-116).

Enqueues notifications into the PmsNotificationOutbox in the caller's transaction.
Deduplication key prevents duplicate deliveries.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.pms.models import PmsNotificationOutbox

log = logging.getLogger("fusion.pms.notify")

TOPICS = {
    "application.submitted",
    "application.assigned_director",
    "application.reviewed",
    "application.revised",
    "application.resubmitted",
    "application.withdrawn",
    "application.expired",
    "application.appeal_submitted",
    "application.appeal_reviewed",
    "attorney.assigned",
    "attorney.responded",
    "budget.decided",
    "budget.escalated",
    "patent.filed",
    "office_action.recorded",
    "office_action.response_ready",
    "office_action.applicant_approved",
    "office_action.response_submitted",
    "patent.granted",
    "maintenance.decision_requested",
    "maintenance.decided",
    "maintenance.recorded",
    "deadline.alert_30",
    "deadline.alert_15",
    "deadline.alert_5",
    "deadline.escalated",
    "inventor.changed",
    "document.updated",
}


def enqueue_notification(
    *,
    topic: str,
    dedupe_key: str,
    subject: str,
    body: str,
    recipient_user_id: int | None = None,
    recipient_email: str = "",
    payload: dict[str, Any] | None = None,
) -> PmsNotificationOutbox | None:
    """Enqueue a notification inside caller's transaction."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic '{topic}'.")
    if recipient_user_id is None and not recipient_email:
        raise ValueError("A notification needs a recipient user ID or email.")

    try:
        with transaction.atomic():
            return PmsNotificationOutbox.objects.create(
                topic=topic,
                dedupe_key=dedupe_key,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                payload=payload or {},
            )
    except IntegrityError:
        log.debug("pms.notify.duplicate key=%s", dedupe_key)
        return None


def send_pending_notifications(limit: int = 50) -> int:
    """Drain pending notifications from outbox and send via Django email backend."""
    pending = PmsNotificationOutbox.objects.filter(status="pending").order_by("created_at")[:limit]
    sent_count = 0
    for n in pending:
        try:
            recipient = n.recipient_email or f"user{n.recipient_user_id}@fusion.test"
            send_mail(
                subject=n.subject,
                message=n.body,
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
            n.status = "sent"
            n.sent_at = timezone.now()
            n.save(update_fields=["status", "sent_at", "updated_at"])
            sent_count += 1
        except Exception as exc:  # noqa: BLE001
            n.attempts += 1
            n.last_error = str(exc)[:300]
            if n.attempts >= 5:
                n.status = "failed"
            n.save(update_fields=["attempts", "last_error", "status", "updated_at"])
    return sent_count
