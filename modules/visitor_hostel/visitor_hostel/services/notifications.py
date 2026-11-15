"""VHMS notification records and their delivery (UC-VH-023..025, CFR-VH-014).

A notification is written to the outbox in the same transaction as the event
that caused it, so a broken mail server never fails a booking (UC-VH-023
minimal guarantee). Delivery itself is a worker's job; `dedupe_key` makes it
safe to run twice.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.visitor_hostel.models import NotificationOutbox

log = logging.getLogger("fusion.visitor_hostel.notify")

TOPICS = {
    "booking.submitted",              # AFR-VH-076
    "booking.approved",               # AFR-VH-077
    "booking.rejected",               # AFR-VH-077, AFR-VH-020
    "modification.requested",         # AFR-VH-078
    "modification.confirmed",         # AFR-VH-078
    "cancellation.requested",         # AFR-VH-078
    "cancellation.confirmed",         # AFR-VH-078
    "stay.checkin_reminder",          # AFR-VH-079
    "stay.checkout_reminder",         # AFR-VH-079
    "inventory.below_threshold",      # BR-VH-043, AFR-VH-080
}

CLAIM_TIMEOUT = timedelta(minutes=10)


def enqueue(*, topic: str, dedupe_key: str, recipient_user_id: int | None,
            subject: str, body: str, payload: dict | None = None
            ) -> NotificationOutbox | None:
    """Queue one notification inside the caller's transaction. None when there
    is nobody to send to, or it was already queued."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None:
        log.info("visitor_hostel.notify.no_recipient topic=%s key=%s", topic, dedupe_key)
        return None
    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key[:200],
                recipient_user_id=recipient_user_id, subject=subject[:200],
                body=body, payload=payload or {})
    except IntegrityError:
        return None


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return f"sent={self.sent} failed={self.failed} deferred={self.deferred}"


def _claim(row: NotificationOutbox) -> bool:
    """One conditional UPDATE, so of two workers exactly one sends."""
    return NotificationOutbox.objects.filter(pk=row.pk, status="pending").update(
        status="sending", claimed_at=timezone.now()) == 1


def _fail(row: NotificationOutbox, error: str, max_attempts: int) -> None:
    row.attempts += 1
    row.last_error = error[:300]
    row.status = "failed" if row.attempts >= max_attempts else "pending"
    row.claimed_at = None
    row.save(update_fields=["attempts", "last_error", "status", "claimed_at",
                            "updated_at"])


def _ready(row: NotificationOutbox, now) -> bool:
    if row.attempts == 0:
        return True
    return now - row.updated_at >= timedelta(minutes=2 ** (row.attempts - 1))


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    now = now or timezone.now()
    NotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=now - CLAIM_TIMEOUT,
    ).update(status="pending", claimed_at=None)

    limit = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    report = DeliveryReport()
    queue = list(NotificationOutbox.objects.filter(status="pending")
                 .order_by("created_at")[:limit])
    if not queue:
        return report

    try:
        people = directory.get_users(sorted({r.recipient_user_id for r in queue}))
    except Exception as exc:                                   # noqa: BLE001
        log.warning("visitor_hostel.notify.directory_unavailable err=%s", exc)
        report.deferred = len(queue)
        return report

    for row in queue:
        if not _ready(row, now):
            report.deferred += 1
            continue
        person = people.get(row.recipient_user_id)
        if person is None or not person.email:
            _fail(row, "No email address on record for this recipient.", max_attempts)
            report.failed += 1
            continue
        if not _claim(row):
            report.deferred += 1
            continue
        try:
            send_mail(subject=row.subject, message=row.body,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[person.email], fail_silently=False)
        except Exception as exc:                               # noqa: BLE001
            _fail(row, f"{exc.__class__.__name__}: {exc}", max_attempts)
            report.failed += 1
            continue
        row.status, row.sent_at, row.claimed_at = "sent", timezone.now(), None
        row.attempts += 1
        row.last_error = ""
        row.save(update_fields=["status", "sent_at", "claimed_at", "attempts",
                                "last_error", "updated_at"])
        report.sent += 1
    return report


# -- Booking lifecycle events (UC-VH-023) --------------------------------------
def _visitor(booking) -> str:
    return (f"{booking.visitor_name} ({booking.arrival_date:%d %b %Y} to "
            f"{booking.departure_date:%d %b %Y})")


def booking_event(booking, topic: str, *, detail: str = "", key_suffix: str = "") -> None:
    """Addressed to the Indenter, the one recipient the PS names. An offline
    booking with no Indenter has nobody inside VHMS to tell."""
    subjects = {
        "booking.submitted": "Visitors Hostel booking received",
        "booking.approved": "Visitors Hostel booking approved",
        "booking.rejected": "Visitors Hostel booking not approved",
        "modification.requested": "Booking modification request recorded",
        "modification.confirmed": "Booking modification confirmed",
        "cancellation.requested": "Booking cancellation request recorded",
        "cancellation.confirmed": "Booking cancelled",
    }
    body = f"Booking #{booking.pk} for {_visitor(booking)} is now {booking.status}."
    if detail:
        body += f"\n\n{detail}"
    enqueue(topic=topic,
            dedupe_key=f"vh:{topic}:{booking.pk}:{key_suffix or booking.status}",
            recipient_user_id=booking.indenter_user_id,
            subject=f"{subjects[topic]} — #{booking.pk}", body=body,
            payload={"booking_id": booking.pk, "status": booking.status})
