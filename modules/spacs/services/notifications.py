"""Transactional notification outbox enqueueing and dispatch for SPACS.

Enforces:
- CFR-SPACS-015 (Lifecycle Notifications)
- BR-SPACS-008 (Notification on Significant Status Change)
- AFR-SPACS-048
- Deduplicated enqueueing (not exactly-once external delivery)
- Notification failures never alter business application or task state
"""
from __future__ import annotations

import logging
from typing import Any
from django.db import IntegrityError, transaction
from modules.spacs.models import SpacsNotificationOutbox

log = logging.getLogger("fusion.spacs.notify")

TOPICS = {
    "application.submitted",
    "application.resubmitted",
    "application.verified",
    "application.verification_concern",
    "application.correction_required",
    "application.decided",
    "application.withdrawn",
    "renewal.reminder",
    "award.published",
    "sla.reminder",
    "sla.escalation",
}


def enqueue(
    topic: str,
    dedupe_key: str,
    subject: str,
    body: str,
    recipient_user_id: int | None = None,
    recipient_email: str = "",
    payload: dict[str, Any] | None = None,
) -> SpacsNotificationOutbox | None:
    """Queues a notification into the transactional outbox.

    Returns the created outbox row, or None if already enqueued with the same dedupe_key.
    Does NOT guarantee external delivery; guarantees deduplicated enqueueing.
    """
    if topic not in TOPICS:
        raise ValueError(f"Unknown SPACS notification topic {topic!r}.")

    if recipient_user_id is None and not recipient_email:
        raise ValueError("A notification requires a recipient user_id or email.")

    try:
        with transaction.atomic():
            return SpacsNotificationOutbox.objects.create(
                topic=topic,
                dedupe_key=dedupe_key,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                payload=payload or {},
                status="pending",
            )
    except IntegrityError:
        log.debug("spacs.notify.duplicate_suppressed key=%s", dedupe_key)
        return None


# -- Outbox Delivery Mechanism -------------------------------------------------

@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return f"sent={self.sent} failed={self.failed} deferred={self.deferred}"


def _claim(row: SpacsNotificationOutbox) -> bool:
    """Takes exclusive ownership of a row via conditional update."""
    from django.utils import timezone
    return (
        SpacsNotificationOutbox.objects.filter(pk=row.pk, status="pending")
        .update(status="sending", claimed_at=timezone.now()) == 1
    )


def deliver_pending(limit: int = 200) -> DeliveryReport:
    """Drains the SPACS notification outbox.

    Queued, sending, sent, and failed states are tracked.
    Failed deliveries can be retried up to MAX_ATTEMPTS.
    Failures never alter business state.
    """
    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils import timezone
    from modules.directory import contracts as directory

    now = timezone.now()
    report = DeliveryReport()
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)

    pending_rows = list(
        SpacsNotificationOutbox.objects.filter(status="pending").order_by("created_at")[:limit]
    )

    for row in pending_rows:
        if not _claim(row):
            continue

        email = row.recipient_email
        if not email and row.recipient_user_id:
            users = directory.get_users([row.recipient_user_id])
            user_dto = users.get(row.recipient_user_id)
            if user_dto:
                email = user_dto.email

        if not email:
            # Cannot deliver without email
            row.status = "suppressed"
            row.last_error = "No recipient email found"
            row.save()
            report.failed += 1
            continue

        try:
            send_mail(
                subject=row.subject,
                message=row.body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "SPACS Office <spacs@iiitdmj.ac.in>"),
                recipient_list=[email],
                fail_silently=False,
            )
            row.status = "sent"
            row.sent_at = timezone.now()
            row.save()
            report.sent += 1
        except Exception as exc:
            log.warning("spacs.notify.delivery_failed id=%s error=%s", row.pk, exc)
            row.attempts += 1
            row.last_error = str(exc)[:280]
            if row.attempts >= max_attempts:
                row.status = "failed"
            else:
                row.status = "pending"  # Eligible for retry
            row.save()
            report.failed += 1

    return report
