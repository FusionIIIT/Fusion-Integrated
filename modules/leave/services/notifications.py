"""Notification decisions and delivery (BR-EL-035, ADR-0006).

The ELM outbox is its own table rather than a shared one: leave notifications
are written in the same transaction as leave decisions, and sharing a table
across modules would make one module's rollback silently drop another's mail.
The delivery algorithm is the same shape as every other module's, because the
failure modes are the same.
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
from modules.leave.models import NotificationOutbox
from modules.leave.models.outbox import (
    FAILED,
    PENDING,
    SENDING,
    SENT,
    SUPPRESSED,
    TOPICS,
)

log = logging.getLogger("fusion.leave.notify")

#: A row unresolved this long is assumed orphaned and returned to the queue.
CLAIM_TIMEOUT = timedelta(minutes=10)


def enqueue(*, topic: str, dedupe_key: str, subject: str, body: str,
            recipient_user_id: int | None = None, recipient_email: str = "",
            payload: dict | None = None) -> NotificationOutbox | None:
    """Queue one notification, inside the caller's transaction. None if it was
    already queued, so a retried decision cannot double-notify."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None and not recipient_email:
        raise ValueError("A notification needs a recipient.")
    try:
        # Nested, so a duplicate key cannot poison the caller's transaction.
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key, subject=subject, body=body,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email, payload=payload or {},
            )
    except IntegrityError:
        log.debug("leave.notify.duplicate key=%s", dedupe_key)
        return None


def enqueue_many(rows: list[dict]) -> int:
    """Fan-out, one at a time so a single duplicate does not drop the batch."""
    return sum(1 for row in rows if enqueue(**row) is not None)


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    skipped_capped: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return (f"sent={self.sent} failed={self.failed} "
                f"capped={self.skipped_capped} deferred={self.deferred}")


def _backoff_ready(row: NotificationOutbox, now) -> bool:
    """1, 2, 4, 8… minutes, so a dead address stops drowning the log."""
    if row.attempts == 0:
        return True
    return (now - row.updated_at) >= timedelta(minutes=2 ** (row.attempts - 1))


def _sent_today(recipient_user_id: int | None, now) -> int:
    if recipient_user_id is None:
        return 0
    return NotificationOutbox.objects.filter(
        recipient_user_id=recipient_user_id, status=SENT,
        sent_at__gte=now - timedelta(hours=24)).count()


def _reclaim_stranded(now) -> int:
    return NotificationOutbox.objects.filter(
        status=SENDING, claimed_at__lt=now - CLAIM_TIMEOUT
    ).update(status=PENDING, claimed_at=None)


def _claim(row: NotificationOutbox) -> bool:
    """Take exclusive ownership before sending, never after: of two workers
    holding one pending row exactly one proceeds."""
    return NotificationOutbox.objects.filter(
        pk=row.pk, status=PENDING,
    ).update(status=SENDING, claimed_at=timezone.now()) == 1


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    now = now or timezone.now()
    _reclaim_stranded(now)
    limit = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    daily_cap = getattr(settings, "NOTIFY_DAILY_CAP_PER_RECIPIENT", 20)
    report = DeliveryReport()

    queue = list(NotificationOutbox.objects.filter(status=PENDING)
                 .order_by("created_at")[:limit])
    addresses = _resolve_addresses(queue)

    for row in queue:
        if not _backoff_ready(row, now):
            report.deferred += 1
            continue

        to = row.recipient_email or addresses.get(row.recipient_user_id or -1, "")
        if not to:
            _fail(row, "No email address on record for this recipient.", max_attempts)
            report.failed += 1
            continue

        if _sent_today(row.recipient_user_id, now) >= daily_cap:
            # Suppressed, not failed: the decision was right, the volume is not.
            row.status = SUPPRESSED
            row.last_error = f"Daily cap of {daily_cap} reached."
            row.save(update_fields=["status", "last_error", "updated_at"])
            report.skipped_capped += 1
            continue

        if not _claim(row):
            report.deferred += 1
            continue

        try:
            send_mail(subject=row.subject, message=row.body,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[to], fail_silently=False)
        except Exception as exc:                                   # noqa: BLE001
            _fail(row, f"{exc.__class__.__name__}: {exc}"[:300], max_attempts)
            report.failed += 1
            continue

        NotificationOutbox.objects.filter(pk=row.pk).update(
            status=SENT, sent_at=timezone.now(), attempts=row.attempts + 1,
            last_error="", claimed_at=None, updated_at=timezone.now())
        report.sent += 1

    left = NotificationOutbox.objects.filter(status=PENDING).count()
    if left:
        # Never let "sent 500" read as "drained the queue".
        log.info("leave.notify.backlog remaining=%d", left)
    return report


def _fail(row: NotificationOutbox, error: str, max_attempts: int) -> None:
    attempts = row.attempts + 1
    status = FAILED if attempts >= max_attempts else PENDING
    if status == FAILED:
        log.warning("leave.notify.giving_up id=%s topic=%s err=%s",
                    row.pk, row.topic, error)
    NotificationOutbox.objects.filter(pk=row.pk).update(
        attempts=attempts, status=status, last_error=error, claimed_at=None,
        updated_at=timezone.now())


def _resolve_addresses(rows: list[NotificationOutbox]) -> dict[int, str]:
    """One batched directory call for the whole run."""
    ids = {r.recipient_user_id for r in rows
           if r.recipient_user_id and not r.recipient_email}
    if not ids:
        return {}
    try:
        people = directory.get_users(sorted(ids))
    except Exception as exc:                                       # noqa: BLE001
        log.warning("leave.notify.directory_unavailable err=%s", exc)
        return {}
    return {uid: p.email for uid, p in people.items() if p.email}