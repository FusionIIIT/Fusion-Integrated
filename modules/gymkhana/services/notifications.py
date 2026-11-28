"""Notifications (AFR-GYM-013, 015, 025): queued with their cause, drained outside the request."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory
from modules.gymkhana.models import NotificationOutbox, PollTarget

log = logging.getLogger("fusion.gymkhana.notify")

SESSION_BOOKED = "session.booked"
EVENT_BOOKED = "event.booked"
POLL_CREATED = "poll.created"
TOPICS = {SESSION_BOOKED, EVENT_BOOKED, POLL_CREATED}

CLAIM_TIMEOUT = timedelta(minutes=10)
MAX_ATTEMPTS = 5
DEFAULT_LIMIT = 500


def enqueue(*, topic: str, dedupe_key: str, subject: str, body: str,
            recipient_user_id: int | None = None, is_broadcast: bool = False,
            payload: dict | None = None) -> NotificationOutbox | None:
    """Queue one row inside the caller's transaction; None if that key is already queued."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None and not is_broadcast:
        raise ValueError("A notification needs a recipient or must be a broadcast.")
    try:
        # A savepoint, so a duplicate key cannot poison the caller's transaction.
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key, subject=subject, body=body,
                recipient_user_id=recipient_user_id, is_broadcast=is_broadcast,
                payload=payload or {})
    except IntegrityError:
        return None


def enqueue_to_users(*, topic: str, key: str, subject: str, body: str,
                     user_ids, payload: dict | None = None) -> int:
    """One row per recipient, skipping any already queued; returns the recipients considered."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    rows = [NotificationOutbox(topic=topic, dedupe_key=f"{key}:u{uid}", subject=subject,
                               body=body, recipient_user_id=uid, payload=payload or {})
            for uid in sorted(set(user_ids))]
    NotificationOutbox.objects.bulk_create(rows, ignore_conflicts=True)
    return len(rows)


@dataclass
class DeliveryReport:
    expanded: int = 0
    sent: int = 0
    failed: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return (f"expanded={self.expanded} sent={self.sent} failed={self.failed} "
                f"deferred={self.deferred}")


def _claim(row: NotificationOutbox) -> bool:
    """One conditional UPDATE, so of two workers holding the same row exactly one sends it."""
    return NotificationOutbox.objects.filter(pk=row.pk, status="pending").update(
        status="sending", claimed_at=timezone.now()) == 1


def _reclaim_stranded(now) -> int:
    return (NotificationOutbox.objects
            .filter(status="sending", claimed_at__lt=now - CLAIM_TIMEOUT)
            .update(status="pending", claimed_at=None))


def _backoff_ready(row: NotificationOutbox, now) -> bool:
    if row.attempts == 0:
        return True
    return now - row.updated_at >= timedelta(minutes=2 ** (row.attempts - 1))


def _fail(row: NotificationOutbox, error: str) -> None:
    row.attempts += 1
    row.last_error = error[:300]
    row.status = "failed" if row.attempts >= MAX_ATTEMPTS else "pending"
    row.claimed_at = None
    row.save(update_fields=["attempts", "last_error", "status", "claimed_at", "updated_at"])
    if row.status == "failed":
        log.warning("gymkhana.notify.giving_up id=%s topic=%s", row.pk, row.topic)


def _expand(row: NotificationOutbox, report: DeliveryReport) -> None:
    """A poll broadcast becomes one row per targeted student (BR-GYM-013)."""
    if not _claim(row):
        report.deferred += 1
        return
    poll_id = (row.payload or {}).get("poll_id")
    targets = list(PollTarget.objects.filter(poll_id=poll_id)
                   .values_list("batch_year", "discipline"))
    try:
        recipients: set[int] = set()
        for batch_year, discipline in targets:
            recipients.update(directory.students_in_cohorts(
                [batch_year], [discipline] if discipline else []))
    except IamUnavailable as exc:
        _fail(row, f"directory unavailable: {exc.__class__.__name__}")
        report.failed += 1
        return
    made = enqueue_to_users(topic=row.topic, key=row.dedupe_key, subject=row.subject,
                            body=row.body, user_ids=recipients, payload=row.payload)
    row.status = "sent"
    row.sent_at = timezone.now()
    row.claimed_at = None
    row.last_error = f"Expanded to {len(recipients)} recipient(s)."
    row.save(update_fields=["status", "sent_at", "claimed_at", "last_error", "updated_at"])
    report.expanded += made


def _addresses(rows) -> dict[int, str]:
    ids = sorted({r.recipient_user_id for r in rows if r.recipient_user_id})
    if not ids:
        return {}
    return {uid: p.email for uid, p in directory.get_users(ids).items() if p.email}


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    """Drain the outbox; safe to run concurrently and to re-run."""
    now = now or timezone.now()
    limit = limit or DEFAULT_LIMIT
    report = DeliveryReport()
    _reclaim_stranded(now)

    for row in NotificationOutbox.objects.filter(status="pending", is_broadcast=True) \
            .order_by("created_at")[:limit]:
        _expand(row, report)

    queue = list(NotificationOutbox.objects.filter(status="pending", is_broadcast=False)
                 .order_by("created_at")[:limit])
    addresses = _addresses(queue)
    for row in queue:
        if not _backoff_ready(row, now):
            report.deferred += 1
            continue
        to = addresses.get(row.recipient_user_id or -1, "")
        if not to:
            _fail(row, "No email address on record for this recipient.")
            report.failed += 1
            continue
        if not _claim(row):
            report.deferred += 1
            continue
        try:
            send_mail(subject=row.subject, message=row.body,
                      from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[to],
                      fail_silently=False)
        # The mail backend raises many types; each is recorded on the row and retried.
        except Exception as exc:  # noqa: BLE001
            _fail(row, f"{exc.__class__.__name__}: {exc}")
            report.failed += 1
            continue
        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.claimed_at = None
        row.save(update_fields=["status", "sent_at", "attempts", "last_error",
                                "claimed_at", "updated_at"])
        report.sent += 1
    return report
