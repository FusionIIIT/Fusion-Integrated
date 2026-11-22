"""Notification decisions and delivery (BR-MMS-035/022; PS §3.3.10).

Every notification is written to the outbox in the same transaction as the
event that caused it, so a decision and its email commit together and a
broken mail server can never fail a student's request. `dedupe_key` makes
redelivery idempotent.

MMS triggers notifications only for the PS-listed events and does not own
the external email delivery infrastructure.
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
from modules.mms.models import NotificationOutbox

log = logging.getLogger("fusion.mms.notify")

# Anything not listed is a programming error (BR-MMS-035).
TOPICS = {
    "registration.submitted",
    "registration.decided",
    "deregistration.submitted",
    "deregistration.decided",
    "rebate.submitted",
    "rebate.decided",
    "special_food.submitted",
    "special_food.decided",
    "special_food.fulfilled",
    "special_food.default_rejected",
    "survey.created",
    "survey.reminder",
    "survey.default_no",
    "menu.updated",
    "bill.published",
    "announcement.published",
}


def enqueue(
    *,
    topic: str,
    dedupe_key: str,
    subject: str,
    body: str,
    recipient_user_id: int | None = None,
    recipient_email: str = "",
    payload: dict | None = None,
) -> NotificationOutbox | None:
    """Queue one notification, inside the caller's transaction. None if it was
    already queued."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None and not recipient_email:
        raise ValueError("A notification needs a recipient.")

    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic,
                dedupe_key=dedupe_key,
                subject=subject,
                body=body,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email,
                payload=payload or {},
            )
    except IntegrityError:
        log.debug("mms.notify.duplicate key=%s", dedupe_key)
        return None


def enqueue_many(rows: list[dict]) -> int:
    return sum(1 for r in rows if enqueue(**r) is not None)


@dataclass
class DeliveryReport:
    expanded: int = 0
    sent: int = 0
    failed: int = 0
    skipped_capped: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return (
            f"expanded={self.expanded} sent={self.sent} "
            f"failed={self.failed} capped={self.skipped_capped} "
            f"deferred={self.deferred}"
        )


def _backoff_ready(row: NotificationOutbox, now) -> bool:
    if row.attempts == 0:
        return True
    wait = timedelta(minutes=2 ** (row.attempts - 1))
    return (now - row.updated_at) >= wait


def _sent_today(recipient_user_id: int | None, now) -> int:
    if recipient_user_id is None:
        return 0
    since = now - timedelta(hours=24)
    return NotificationOutbox.objects.filter(
        recipient_user_id=recipient_user_id, status="sent", sent_at__gte=since
    ).count()


CLAIM_TIMEOUT = timedelta(minutes=10)


def _reclaim_stranded(now) -> int:
    return NotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=now - CLAIM_TIMEOUT
    ).update(status="pending", claimed_at=None)


def _claim(row) -> bool:
    return (
        NotificationOutbox.objects.filter(
            pk=row.pk,
            status="pending",
        ).update(status="sending", claimed_at=timezone.now())
        == 1
    )


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    """Drain the outbox. Safe to run concurrently and safe to re-run."""
    now = now or timezone.now()
    _reclaim_stranded(now)
    limit = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    daily_cap = getattr(settings, "NOTIFY_DAILY_CAP_PER_RECIPIENT", 20)
    report = DeliveryReport()

    queue = list(NotificationOutbox.objects.filter(status="pending").order_by("created_at")[:limit])

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
            row.status = "suppressed"
            row.last_error = f"Daily cap of {daily_cap} reached."
            row.save(update_fields=["status", "last_error", "updated_at"])
            report.skipped_capped += 1
            continue

        if not _claim(row):
            report.deferred += 1
            continue

        try:
            send_mail(
                subject=row.subject,
                message=row.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001
            _fail(row, f"{exc.__class__.__name__}: {exc}"[:300], max_attempts)
            report.failed += 1
            continue

        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.claimed_at = None
        row.save(
            update_fields=[
                "status",
                "sent_at",
                "attempts",
                "last_error",
                "claimed_at",
                "updated_at",
            ]
        )
        report.sent += 1

    left = NotificationOutbox.objects.filter(status="pending").count()
    if left:
        log.info("mms.notify.backlog remaining=%d", left)
    return report


def _fail(row: NotificationOutbox, error: str, max_attempts: int) -> None:
    row.attempts += 1
    row.last_error = error
    if row.attempts >= max_attempts:
        row.status = "failed"
    else:
        row.status = "pending"
    row.claimed_at = None
    row.save(update_fields=["attempts", "last_error", "status", "claimed_at", "updated_at"])


def _resolve_addresses(rows: list[NotificationOutbox]) -> dict[int, str]:
    ids = {r.recipient_user_id for r in rows if r.recipient_user_id and not r.recipient_email}
    if not ids:
        return {}
    try:
        people = directory.get_users(sorted(ids))
    except Exception:  # noqa: BLE001
        return {}
    return {uid: p.email for uid, p in people.items() if p.email}
