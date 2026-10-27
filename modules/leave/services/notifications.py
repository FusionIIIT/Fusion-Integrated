"""Leave notification enqueueing and idempotent delivery."""
from __future__ import annotations

import logging
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from modules.leave.models import LeaveNotificationOutbox

log = logging.getLogger("fusion.leave.notify")


def enqueue(*, recipient_user_id: int | None, topic: str, dedupe_key: str,
            subject: str, body: str) -> LeaveNotificationOutbox | None:
    if not recipient_user_id:
        return None
    try:
        with transaction.atomic():
            return LeaveNotificationOutbox.objects.create(
                recipient_user_id=recipient_user_id, topic=topic, dedupe_key=dedupe_key,
                subject=subject, body=body,
            )
    except IntegrityError:
        return None


def deliver_pending(*, limit: int = 200) -> dict[str, int]:
    report = {"sent": 0, "failed": 0, "deferred": 0}
    now = timezone.now()
    LeaveNotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=now - timedelta(minutes=10)
    ).update(status="pending", claimed_at=None)
    pending = list(LeaveNotificationOutbox.objects.filter(status="pending").order_by("created_at")[:limit])
    if not pending:
        return report
    try:
        from modules.directory import contracts as directory
        recipients = directory.get_users(sorted({row.recipient_user_id for row in pending}))
    except Exception as exc:  # directory outages must leave the outbox retryable
        log.warning("leave.notify.directory_unavailable err=%s", exc)
        report["deferred"] = len(pending)
        return report

    for row in pending:
        person = recipients.get(row.recipient_user_id)
        email = getattr(person, "email", "") if person else ""
        if not email:
            row.attempts += 1
            row.last_error = "No email address on record for recipient."
            if row.attempts >= 5:
                row.status = "failed"
                row.save(update_fields=["attempts", "last_error", "status", "updated_at"])
                report["failed"] += 1
            else:
                row.save(update_fields=["attempts", "last_error", "updated_at"])
                report["deferred"] += 1
            continue
        claimed = LeaveNotificationOutbox.objects.filter(pk=row.pk, status="pending").update(
            status="sending", claimed_at=timezone.now()
        )
        if not claimed:
            report["deferred"] += 1
            continue
        try:
            send_mail(row.subject, row.body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        except Exception as exc:  # noqa: BLE001
            row.attempts += 1
            row.last_error = f"{exc.__class__.__name__}: {exc}"[:300]
            row.status = "failed" if row.attempts >= 5 else "pending"
            row.claimed_at = None
            row.save(update_fields=["attempts", "last_error", "status", "claimed_at", "updated_at"])
            report["failed" if row.status == "failed" else "deferred"] += 1
            continue
        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.claimed_at = None
        row.save(update_fields=["status", "sent_at", "attempts", "last_error", "claimed_at", "updated_at"])
        report["sent"] += 1
    return report
