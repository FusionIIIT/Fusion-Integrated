from __future__ import annotations

import logging
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.badms.models import NotificationOutbox
from modules.badms.services import audit
from modules.directory import contracts as directory

log = logging.getLogger("fusion.badms.notifications")
MAX_ATTEMPTS = 8
CLAIM_TIMEOUT = timedelta(minutes=10)


def enqueue_emails(*, recipients: list[str], subject: str, body: str,
                   resource: str, resource_id: str) -> int:
    addresses = sorted({email.strip() for email in recipients if email.strip()})
    if not addresses:
        audit.record(
            actor_user_id=None,
            action="notification_unconfigured",
            resource=resource,
            resource_id=resource_id,
            outcome="failure",
            details={"reason": "recipient_not_configured"},
        )
        return 0
    valid_addresses = []
    for email in addresses:
        try:
            validate_email(email)
        except ValidationError:
            audit.record(
                actor_user_id=None,
                action="notification_unconfigured",
                resource=resource,
                resource_id=resource_id,
                outcome="failure",
                details={"reason": "invalid_recipient_address"},
            )
        else:
            valid_addresses.append(email)
    if not valid_addresses:
        return 0
    now = timezone.now()
    NotificationOutbox.objects.bulk_create([
        NotificationOutbox(
            recipient_email=email,
            subject=subject[:200],
            body=body[:4000],
            next_attempt_at=now,
        )
        for email in valid_addresses
    ])
    return len(valid_addresses)


def enqueue_user(*, user_id: int, subject: str, body: str,
                 resource: str, resource_id: str) -> None:
    NotificationOutbox.objects.create(
        recipient_user_id=user_id,
        subject=subject[:200],
        body=body[:4000],
        next_attempt_at=timezone.now(),
    )


def _claim(now) -> NotificationOutbox | None:
    with transaction.atomic():
        row = (
            NotificationOutbox.objects.select_for_update()
            .filter(
                Q(status=NotificationOutbox.Status.PENDING,
                  next_attempt_at__lte=now)
                | Q(status=NotificationOutbox.Status.SENDING,
                    claimed_at__lte=now - CLAIM_TIMEOUT)
            )
            .order_by("created_at")
            .first()
        )
        if row is None:
            return None
        row.status = NotificationOutbox.Status.SENDING
        row.claimed_at = now
        row.attempts += 1
        row.save(update_fields=["status", "claimed_at", "attempts"])
        return row


def _finish(row_id: int, *, error_code: str = "") -> None:
    now = timezone.now()
    with transaction.atomic():
        row = NotificationOutbox.objects.select_for_update().get(pk=row_id)
        row.claimed_at = None
        if not error_code:
            row.status = NotificationOutbox.Status.SENT
            row.sent_at = now
            row.error_code = ""
        else:
            row.error_code = error_code[:80]
            if row.attempts >= MAX_ATTEMPTS:
                row.status = NotificationOutbox.Status.FAILED
            else:
                row.status = NotificationOutbox.Status.PENDING
                delay = min(60 * (2 ** (row.attempts - 1)), 3600)
                row.next_attempt_at = now + timedelta(seconds=delay)
        row.save(update_fields=[
            "status", "claimed_at", "sent_at", "error_code", "next_attempt_at",
        ])


def deliver_pending(*, limit: int = 100) -> dict[str, int]:
    sent = 0
    failed = 0
    for _ in range(limit):
        row = _claim(timezone.now())
        if row is None:
            break
        error_code = ""
        try:
            recipient = row.recipient_email
            if not recipient and row.recipient_user_id is not None:
                try:
                    person = directory.get_users([row.recipient_user_id]).get(
                        row.recipient_user_id,
                    )
                except IamUnavailable:
                    person = None
                    error_code = "directory_unavailable"
                if not error_code:
                    recipient = person.email if person else ""
                    if not recipient:
                        error_code = "recipient_email_unavailable"
                    else:
                        row.recipient_email = recipient
                        row.save(update_fields=["recipient_email"])
            if not recipient and not error_code:
                error_code = "recipient_not_configured"
            if error_code:
                _finish(row.pk, error_code=error_code)
                failed += 1
                continue
            result = send_mail(
                row.subject,
                row.body,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
            if result != 1:
                error_code = "mail_not_sent"
        except (SMTPException, OSError) as exc:
            error_code = type(exc).__name__
        _finish(row.pk, error_code=error_code)
        if error_code:
            failed += 1
            log.error("badms.notification.failed outbox_id=%s error_code=%s",
                      row.pk, error_code)
        else:
            sent += 1
    return {"sent": sent, "failed": failed}
