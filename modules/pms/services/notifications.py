"""PMS notification outbox delivery through Fusion's configured email backend."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from modules.pms.models import PmsNotification

log = logging.getLogger("fusion.pms.notify")


def _send_notification(row, email):
    if not email:
        raise ValueError("Recipient has no email address in the Fusion directory.")
    send_mail(row.subject, row.body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)


CLAIM_TIMEOUT = timedelta(minutes=10)


def deliver_pending(limit=250, now=None):
    now = now or timezone.now()
    PmsNotification.objects.filter(status="sending", claimed_at__lt=now - CLAIM_TIMEOUT).update(
        status="queued", claimed_at=None
    )
    rows = list(PmsNotification.objects.filter(status="queued").order_by("created_at")[:limit])
    sent = failed = 0
    from modules.directory import contracts as directory

    for row in rows:
        retry_after = timedelta(minutes=min(60, 2**row.attempts))
        if row.last_attempt_at and now - row.last_attempt_at < retry_after:
            continue
        if not PmsNotification.objects.filter(pk=row.pk, status="queued").update(
            status="sending", claimed_at=now, last_attempt_at=now
        ):
            continue
        try:
            people = directory.get_users([row.recipient_user_id])
            person = people.get(row.recipient_user_id)
            email = getattr(person, "email", "") if person else ""
            _send_notification(row, email)
        except Exception as exc:  # noqa: BLE001  # Retry every delivery-backend failure.
            row.attempts += 1
            row.last_error = f"{type(exc).__name__}: {exc}"[:300]
            row.status = (
                "failed"
                if row.attempts >= getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
                else "queued"
            )
            row.claimed_at = None
            row.save(update_fields=["attempts", "last_error", "status", "claimed_at"])
            failed += 1
            log.warning("pms.notify.failed id=%s attempt=%s", row.pk, row.attempts)
            continue
        row.status = "sent"
        row.sent_at = now
        row.claimed_at = None
        row.last_error = ""
        row.save(update_fields=["status", "sent_at", "claimed_at", "last_error"])
        sent += 1
    return {"sent": sent, "failed": failed}
