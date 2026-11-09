"""Transactional notification trigger and outbox handling for MMS events."""
from __future__ import annotations

import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.mms.models import NotificationOutbox

log = logging.getLogger("fusion.mms.notify")

TOPICS = {
    "request.submitted", "request.decided", "menu.updated", "bill.published",
    "rebate.submitted", "rebate.decided", "vacation.created",
    "vacation.reminder", "special_food.submitted", "special_food.decided",
    "special_food.fulfillment", "announcement.published",
}


def enqueue(*, topic: str, dedupe_key: str, subject: str, body: str,
            recipient_user_id: int | None = None,
            recipient_email: str = "") -> NotificationOutbox | None:
    if topic not in TOPICS:
        raise ValueError(f"Unrecognized MMS notification topic: {topic}")
    if recipient_user_id is None and not recipient_email:
        raise ValueError("An MMS notification must have a recipient.")
    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key, subject=subject, body=body,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email)
    except IntegrityError:
        return None


def notify_user(*, topic: str, key: str, user_id: int,
                subject: str, body: str) -> None:
    enqueue(topic=topic, dedupe_key=key, recipient_user_id=user_id,
            subject=subject, body=body)


def notify_students(*, topic: str, key: str, user_ids: list[int],
                    subject: str, body: str) -> int:
    made = 0
    for user_id in sorted(set(user_ids)):
        made += enqueue(
            topic=topic, dedupe_key=f"{key}:u{user_id}",
            recipient_user_id=user_id, subject=subject, body=body) is not None
    return made


def deliver_pending(*, limit: int | None = None) -> dict[str, int]:
    from modules.directory import contracts as directory

    now = timezone.now()
    NotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=now - timedelta(minutes=10)).update(
            status="pending", claimed_at=None)
    rows = list(NotificationOutbox.objects.filter(status="pending")
                .order_by("created_at")[:limit or settings.NOTIFY_MAX_PER_RUN])
    ids = {row.recipient_user_id for row in rows
           if row.recipient_user_id and not row.recipient_email}
    people = directory.get_users(sorted(ids)) if ids else {}
    sent = failed = 0
    for row in rows:
        address = row.recipient_email or getattr(people.get(row.recipient_user_id), "email", "")
        if not address:
            row.status = "failed"
            row.attempts += 1
            row.last_error = "No institutional email address is available."
            row.save(update_fields=["status", "attempts", "last_error", "updated_at"])
            log.error("mms.notify.no_recipient id=%s user=%s",
                      row.pk, row.recipient_user_id)
            failed += 1
            continue
        claimed = NotificationOutbox.objects.filter(
            pk=row.pk, status="pending").update(
                status="sending", claimed_at=timezone.now())
        if not claimed:
            continue
        try:
            send_mail(row.subject, row.body, settings.DEFAULT_FROM_EMAIL,
                      [address], fail_silently=False)
        except (smtplib.SMTPException, OSError) as exc:
            row.status = "failed" if row.attempts + 1 >= settings.NOTIFY_MAX_ATTEMPTS else "pending"
            row.attempts += 1
            row.last_error = f"{exc.__class__.__name__}: {exc}"[:300]
            row.claimed_at = None
            row.save(update_fields=["status", "attempts", "last_error",
                                    "claimed_at", "updated_at"])
            log.warning("mms.notify.delivery_failed id=%s attempt=%s error=%s",
                        row.pk, row.attempts, row.last_error)
            failed += 1
        else:
            row.status = "sent"
            row.sent_at = timezone.now()
            row.attempts += 1
            row.last_error = ""
            row.claimed_at = None
            row.save(update_fields=["status", "sent_at", "attempts", "last_error",
                                    "claimed_at", "updated_at"])
            sent += 1
    return {"sent": sent, "failed": failed}
