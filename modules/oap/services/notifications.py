"""Outbox writes. Each event writes its rows in the caller's transaction (ADR-0006).

An alert is recorded as sent when its row exists, because it is shown in the
portal. An email stays pending until the delivery task has actually sent it.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from modules.oap.models import Notification

log = logging.getLogger("fusion.oap.notify")
MAX_ATTEMPTS = 5


def notify(recipients: Iterable[int], subject: str, body: str) -> None:
    rows = []
    for uid in sorted({int(r) for r in recipients if r is not None}):
        rows.append(
            Notification(
                recipient_user_id=uid,
                channel="alert",
                subject=subject[:200],
                body=body,
                status="sent",
            )
        )
        rows.append(
            Notification(
                recipient_user_id=uid,
                channel="email",
                subject=subject[:200],
                body=body,
                status="pending",
            )
        )
    if rows:
        Notification.objects.bulk_create(rows)


def deliver_pending(limit: int | None = None) -> dict[str, int]:
    from fusion_auth.client import get_client

    batch = Notification.objects.filter(
        channel="email", status__in=["pending", "failed"], attempts__lt=MAX_ATTEMPTS
    ).order_by("created_at")[: limit or 200]
    rows = list(batch)
    if not rows:
        return {"sent": 0, "failed": 0}
    users = get_client().get_users(sorted({r.recipient_user_id for r in rows}))
    sent = failed = 0
    for row in rows:
        row.attempts += 1
        ref = users.get(row.recipient_user_id)
        address = getattr(ref, "email", "") if ref else ""
        if not address:
            row.status, row.last_error = "failed", "no email address on file"
            failed += 1
        else:
            try:
                send_mail(
                    row.subject,
                    row.body,
                    settings.DEFAULT_FROM_EMAIL,
                    [address],
                    fail_silently=False,
                )
                row.status, row.last_error = "sent", ""
                sent += 1
            except Exception as exc:  # noqa: BLE001 — every channel failure is recorded
                row.status, row.last_error = "failed", str(exc)[:500]
                failed += 1
                log.warning("oap.notify.failed id=%s", row.pk)
        row.save(update_fields=["status", "attempts", "last_error", "updated_at"])
    log.info("oap.notify.run sent=%s failed=%s at=%s", sent, failed, timezone.now())
    return {"sent": sent, "failed": failed}
