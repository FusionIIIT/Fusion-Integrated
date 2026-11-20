"""PMS Notification service (CFR-PMS-023, BR-PMS-116).

Enqueues notifications into the PmsNotificationOutbox in the caller's transaction.
Deduplication key prevents duplicate deliveries.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.pms.domain.errors import NotificationRecipientError
from modules.pms.models import PmsNotificationOutbox

log = logging.getLogger("fusion.pms.notify")

#: Configured alert offsets may differ from the seeded 30/15/5, so a
#: numeric suffix is accepted alongside the fixed topic list.
_DEADLINE_ALERT = re.compile(r"deadline\.alert_\d+$")
_CLAIM_TIMEOUT = timedelta(minutes=10)

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
    if topic not in TOPICS and not _DEADLINE_ALERT.match(topic):
        raise ValueError(f"Unknown notification topic '{topic}'.")
    if recipient_user_id is None and not recipient_email:
        # No silent drop and no invented fallback: the workflow's addressee is
        # simply not recorded on this application yet.
        raise NotificationRecipientError("A notification needs a recipient user ID or email.")

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
    """Drain pending notifications without inventing IAM email addresses.

    A conditional state update claims each row before sending, so overlapping
    task executions cannot both deliver the same pending item. Stranded claims
    are returned to pending after a timeout and retried by the next scheduled run.
    """
    now = timezone.now()
    PmsNotificationOutbox.objects.filter(
        status="sending", updated_at__lt=now - _CLAIM_TIMEOUT
    ).update(status="pending", updated_at=now)
    pending = list(
        PmsNotificationOutbox.objects.filter(status="pending")
        .order_by("created_at")[:limit]
    )
    user_ids = {
        row.recipient_user_id
        for row in pending
        if row.recipient_user_id is not None and not row.recipient_email
    }
    addresses = {}
    directory_failed = False
    if user_ids:
        try:
            users = directory.get_users(sorted(user_ids))
            addresses = {user_id: user.email for user_id, user in users.items() if user.email}
        except Exception as exc:  # noqa: BLE001
            log.warning("pms.notify.directory_unavailable err=%s", exc)
            directory_failed = True

    sent_count = 0
    for n in pending:
        recipient = n.recipient_email or addresses.get(n.recipient_user_id)
        if not recipient and directory_failed:
            continue

        claimed_at = timezone.now()
        claimed = PmsNotificationOutbox.objects.filter(
            pk=n.pk, status="pending"
        ).update(status="sending", updated_at=claimed_at)
        if not claimed:
            continue

        max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
        if not recipient:
            n.attempts += 1
            n.last_error = f"No email address is available for user {n.recipient_user_id}."
            n.status = "failed" if n.attempts >= max_attempts else "pending"
            n.save(update_fields=["attempts", "last_error", "status", "updated_at"])
            continue

        try:
            send_mail(
                subject=n.subject,
                message=n.body,
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
            n.status = "sent"
            n.sent_at = timezone.now()
            n.attempts += 1
            n.last_error = ""
            n.save(update_fields=["status", "sent_at", "attempts", "last_error", "updated_at"])
            sent_count += 1
        except Exception as exc:  # noqa: BLE001
            n.attempts += 1
            n.last_error = str(exc)[:300]
            n.status = "failed" if n.attempts >= max_attempts else "pending"
            n.save(update_fields=["attempts", "last_error", "status", "updated_at"])
    return sent_count
