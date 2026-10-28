"""Idempotent email notifications for ELM workflow events."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.elm.models import ELMNotificationOutbox

log = logging.getLogger("fusion.elm.notify")


def enqueue(*, topic: str, dedupe_key: str, recipient_user_id: int,
            subject: str, body: str) -> ELMNotificationOutbox | None:
    if recipient_user_id <= 0:
        raise ValueError("An ELM notification needs a positive recipient user ID.")
    try:
        with transaction.atomic():
            return ELMNotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key,
                recipient_user_id=recipient_user_id,
                subject=subject, body=body)
    except IntegrityError:
        log.debug("elm.notify.duplicate key=%s", dedupe_key)
        return None


def _fail(row: ELMNotificationOutbox, error: str, max_attempts: int) -> None:
    row.attempts += 1
    row.last_error = error[:300]
    row.status = "failed" if row.attempts >= max_attempts else "pending"
    row.claimed_at = None
    row.save(update_fields=(
        "attempts", "last_error", "status", "claimed_at", "updated_at"))


def deliver_pending(*, limit: int | None = None) -> dict[str, int]:
    now = timezone.now()
    claim_timeout = now - timedelta(minutes=10)
    ELMNotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=claim_timeout).update(
            status="pending", claimed_at=None)
    limit = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    rows = list(ELMNotificationOutbox.objects.filter(
        status="pending").order_by("created_at")[:limit])
    user_ids = sorted({row.recipient_user_id for row in rows})
    from modules.directory.contracts import get_users

    users = get_users(user_ids)
    report = {"sent": 0, "failed": 0, "deferred": 0}
    for row in rows:
        if ELMNotificationOutbox.objects.filter(
                pk=row.pk, status="pending").update(
                    status="sending", claimed_at=now) != 1:
            report["deferred"] += 1
            continue
        user = users.get(row.recipient_user_id)
        if user is None or not user.email:
            _fail(row, "Recipient has no email address in the institute directory.",
                  max_attempts)
            report["failed"] += 1
            continue
        try:
            send_mail(
                subject=row.subject, message=row.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email], fail_silently=False)
        except Exception as exc:  # noqa: BLE001
            _fail(row, f"{exc.__class__.__name__}: {exc}", max_attempts)
            report["failed"] += 1
            log.warning("elm.notify.delivery_failed id=%s error=%s", row.pk, exc)
            continue
        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.claimed_at = None
        row.save(update_fields=(
            "status", "sent_at", "attempts", "last_error", "claimed_at",
            "updated_at"))
        report["sent"] += 1
    pending = ELMNotificationOutbox.objects.filter(status="pending").count()
    if pending:
        log.info("elm.notify.backlog remaining=%d", pending)
    return report
