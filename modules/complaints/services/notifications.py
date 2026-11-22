"""CMS outbox delivery; decisions and rows are committed by event services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.complaints.models import NotificationOutbox
from modules.directory import contracts as directory

CLAIM_TIMEOUT = timedelta(minutes=10)


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    deferred: int = 0

    def __str__(self):
        return f"sent={self.sent} failed={self.failed} deferred={self.deferred}"


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    now = now or timezone.now()
    limit = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    report = DeliveryReport()
    _reclaim_stranded(now)
    rows = list(NotificationOutbox.objects.filter(status="pending").order_by("created_at")[:limit])
    addresses = {}
    user_ids = [r.recipient_user_id for r in rows]
    if user_ids:
        try:
            addresses = {i: u.email for i, u in directory.get_users(user_ids).items()}
        except IamUnavailable:
            report.deferred += len(rows)
            return report

    for row in rows:
        if row.attempts and now - row.updated_at < timedelta(minutes=2 ** (row.attempts - 1)):
            report.deferred += 1
            continue
        address = addresses.get(row.recipient_user_id, "")
        if not address:
            _fail(row, "No email address is available for this recipient.", max_attempts)
            report.failed += 1
            continue
        if not _claim(row.pk, now):
            report.deferred += 1
            continue
        try:
            send_mail(
                row.subject, row.body, settings.DEFAULT_FROM_EMAIL, [address], fail_silently=False
            )
        except Exception as exc:  # noqa: BLE001 - persist provider failure and retry
            _fail(row, f"{exc.__class__.__name__}: {exc}"[:300], max_attempts)
            report.failed += 1
            continue
        NotificationOutbox.objects.filter(pk=row.pk, status="sending").update(
            status="sent",
            attempts=row.attempts + 1,
            sent_at=timezone.now(),
            claimed_at=None,
            last_error="",
            updated_at=timezone.now(),
        )
        report.sent += 1
    return report


def _reclaim_stranded(now) -> int:
    return NotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=now - CLAIM_TIMEOUT
    ).update(status="pending", claimed_at=None, updated_at=now)


def _claim(pk: int, now) -> bool:
    return (
        NotificationOutbox.objects.filter(pk=pk, status="pending").update(
            status="sending", claimed_at=now
        )
        == 1
    )


def _fail(row: NotificationOutbox, error: str, max_attempts: int) -> None:
    attempts = row.attempts + 1
    NotificationOutbox.objects.filter(pk=row.pk).update(
        attempts=attempts,
        last_error=error,
        status="failed" if attempts >= max_attempts else "pending",
        claimed_at=None,
        updated_at=timezone.now(),
    )
