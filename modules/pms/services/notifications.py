"""PMS's email outbox: PMS triggers the message, the mail backend delivers it (BR-PMS-116)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.pms.models import Notification

log = logging.getLogger("fusion.pms.notifications")
MAX_ATTEMPTS = 5


def enqueue(*, topic: str, dedupe_key: str, recipient_user_id: int | None, subject: str,
            body: str) -> Notification | None:
    """Queue one email inside the caller's transaction; a repeated key queues nothing."""
    if recipient_user_id is None:
        return None
    try:
        with transaction.atomic():
            return Notification.objects.create(
                topic=topic, dedupe_key=dedupe_key[:200], recipient_user_id=recipient_user_id,
                subject=subject[:200], body=body)
    except IntegrityError:
        return None


def enqueue_many(*, topic: str, key: str, recipients, subject: str, body: str) -> int:
    return sum(1 for uid in dict.fromkeys(recipients)
               if enqueue(topic=topic, dedupe_key=f"{key}:{uid}", recipient_user_id=uid,
                          subject=subject, body=body) is not None)


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return f"sent={self.sent} failed={self.failed} deferred={self.deferred}"


def _claim(row: Notification, now) -> bool:
    """One conditional update decides which worker sends, so a row is never mailed twice."""
    return Notification.objects.filter(pk=row.pk, status="pending",
                                       attempts=row.attempts).update(
        attempts=row.attempts + 1, next_attempt_at=now + timedelta(minutes=10)) == 1


def deliver_pending(*, limit: int = 500, now=None) -> DeliveryReport:
    """Drain due rows; safe to run twice in a row and twice at once."""
    now = now or timezone.now()
    report = DeliveryReport()
    due = list(Notification.objects.filter(status="pending")
               .exclude(next_attempt_at__gt=now).order_by("created_at", "id")[:limit])
    people = directory.get_users([r.recipient_user_id for r in due]) if due else {}
    for row in due:
        if not _claim(row, now):
            report.deferred += 1
            continue
        address = getattr(people.get(row.recipient_user_id), "email", "")
        if not address:
            _fail(row, "No email address on record for this recipient.", final=True)
            report.failed += 1
            continue
        try:
            send_mail(subject=row.subject, message=row.body,
                      from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[address],
                      fail_silently=False)
        except OSError as exc:
            _fail(row, type(exc).__name__, final=row.attempts + 1 >= MAX_ATTEMPTS)
            report.failed += 1
            continue
        Notification.objects.filter(pk=row.pk).update(status="sent", sent_at=timezone.now(),
                                                      last_error="")
        report.sent += 1
    log.info("pms.notify.run notification_ids=%d %s", len(due), report)
    return report


def _fail(row: Notification, error: str, *, final: bool) -> None:
    Notification.objects.filter(pk=row.pk).update(
        status="failed" if final else "pending", last_error=error[:200])
