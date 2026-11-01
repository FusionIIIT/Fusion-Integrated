"""Notification decisions and delivery for department events.

Notifications are written to the outbox in the same transaction as the
event that caused it, ensuring atomicity. `dedupe_key` makes redelivery idempotent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.department.models.notifications import DepartmentNotification
from modules.directory import contracts as directory

log = logging.getLogger("fusion.department.notify")

# Topics defined in the spec.
TOPICS = {
    "stock.requested",
    "stock.authorization_required",
    "stock.issued",
    "stock.rejected",
    "feedback.submitted",
    "feedback.closed",
    "announcement.published",
}


def enqueue(*, topic: str, dedupe_key: str, subject: str, body: str,
            recipient_user_id: int | None = None, payload: dict | None = None) -> DepartmentNotification | None:
    """Queue one notification, inside the caller's transaction. None if it was
    already queued."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None:
        raise ValueError("A notification needs a recipient.")

    try:
        # Nested, so a duplicate key cannot poison the caller's transaction.
        with transaction.atomic():
            return DepartmentNotification.objects.create(
                topic=topic, dedupe_key=dedupe_key, subject=subject, body=body,
                recipient_user_id=recipient_user_id, payload=payload or {},
            )
    except IntegrityError:
        log.debug("department.notify.duplicate key=%s", dedupe_key)
        return None


@dataclass
class DeliveryReport:
    """Report summarizing the delivery attempt."""
    sent: int = 0
    failed: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return f"sent={self.sent} failed={self.failed} deferred={self.deferred}"


#: A row unresolved this long is assumed orphaned and returned to the queue.
CLAIM_TIMEOUT = timedelta(minutes=10)


def _reclaim_stranded(now) -> int:
    """Return rows whose worker died mid-send back to pending."""
    return (DepartmentNotification.objects
            .filter(status="sending", claimed_at__lt=now - CLAIM_TIMEOUT)
            .update(status="pending", claimed_at=None))


def _claim(row) -> bool:
    """Take exclusive ownership of a row, or report that someone else has it."""
    return DepartmentNotification.objects.filter(
        pk=row.pk, status="pending",
    ).update(status="sending", claimed_at=timezone.now()) == 1


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    """Drain the outbox. Safe to run concurrently and safe to re-run."""
    now = now or timezone.now()
    _reclaim_stranded(now)
    limit = limit or 500  # Default limit if not specified
    report = DeliveryReport()

    pending = list(DepartmentNotification.objects
                   .filter(status="pending")
                   .order_by("created_at")[:limit])

    addresses = _resolve_addresses(pending)

    for row in pending:
        # Claim before sending, never after.
        if not _claim(row):
            report.deferred += 1
            continue

        # Resolve recipient email address
        to = addresses.get(row.recipient_user_id, "")

        if not to:
            _fail(row, "No email address on record for this recipient.", max_attempts=1)
            report.failed += 1
            continue

        try:
            # Send mail using Django's standard mail function
            send_mail(
                subject=row.subject, message=row.body,
                from_email="noreply@example.com", # Placeholder email
                recipient_list=[to], fail_silently=False,
            )
        except Exception as exc:
            _fail(row, f"{exc.__class__.__name__}: {exc}", max_attempts=5)
            report.failed += 1
            continue

        # Success path
        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.claimed_at = None
        row.save(update_fields=["status", "sent_at", "attempts", "last_error",
                                "claimed_at", "updated_at"])
        report.sent += 1

    return report


def _fail(row: DepartmentNotification, error: str, max_attempts: int) -> None:
    """Update row state upon failure."""
    row.attempts += 1
    row.last_error = error
    if row.attempts >= max_attempts:
        row.status = "failed"
    else:
        # Back to the queue explicitly, or it sits in "sending" until the sweep.
        row.status = "pending"
    row.claimed_at = None
    row.save(update_fields=["attempts", "last_error", "status", "claimed_at",
                            "updated_at"])


def _resolve_addresses(rows: list[DepartmentNotification]) -> dict[int, str]:
    """One batched directory call for the whole run."""
    ids = {r.recipient_user_id for r in rows
           if r.recipient_user_id}
    if not ids:
        return {}
    try:
        # Use directory.get_users to fetch user details
        people = directory.get_users(sorted(ids))
    except Exception as exc:
        log.warning("department.notify.directory_unavailable err=%s", exc)
        return {}
    return {uid: p.email for uid, p in people.items() if p.email}
