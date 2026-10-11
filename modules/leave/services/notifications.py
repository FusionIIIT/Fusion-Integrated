"""Outbox notifications (SRS-EL-054, SRS-EL-061)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.leave.models import NotificationOutbox

log = logging.getLogger("fusion.leave.notify")

TOPICS = {
    "leave.submitted", "leave.status", "leave.withdrawn", "leave.substitute",
    "leave.decided", "leave.cancelled", "leave.sla.reminder", "leave.sla.escalation",
    "leave.year_end",
}


def enqueue(*, topic: str, dedupe_key: str, subject: str, body: str,
            recipient_user_id: int | None = None, recipient_email: str = "",
            payload: dict | None = None) -> NotificationOutbox | None:
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None and not recipient_email:
        raise ValueError("A notification needs a recipient.")
    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key, subject=subject, body=body,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email, payload=payload or {},
            )
    except IntegrityError:
        return None


def notify_user(user_id: int, *, topic: str, key: str, subject: str, body: str) -> None:
    enqueue(topic=topic, dedupe_key=key, subject=subject, body=body,
            recipient_user_id=user_id)


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0

    def __str__(self) -> str:
        return f"sent={self.sent} failed={self.failed}"


def deliver_pending(limit: int | None = None) -> DeliveryReport:
    cap = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 100)
    rows = list(NotificationOutbox.objects.filter(status="pending")
                .order_by("created_at")[:cap])
    report = DeliveryReport()
    people = directory.get_users([r.recipient_user_id for r in rows if r.recipient_user_id])
    for row in rows:
        email = row.recipient_email
        if not email and row.recipient_user_id:
            person = people.get(row.recipient_user_id)
            email = person.email if person else ""
        if not email:
            row.status = "suppressed"
            row.last_error = "no recipient email"
            row.save(update_fields=["status", "last_error"])
            continue
        try:
            send_mail(row.subject, row.body, None, [email], fail_silently=False)
            row.status = "sent"
            row.sent_at = timezone.now()
            row.save(update_fields=["status", "sent_at"])
            report.sent += 1
        except Exception as exc:  # noqa: BLE001 — drain must continue
            row.status = "failed"
            row.attempts += 1
            row.last_error = str(exc)[:300]
            row.save(update_fields=["status", "attempts", "last_error"])
            report.failed += 1
            log.warning("leave.notify.failed id=%s err=%s", row.pk, exc)
    return report
