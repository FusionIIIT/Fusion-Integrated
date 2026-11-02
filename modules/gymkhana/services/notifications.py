from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.gymkhana.models import NotificationOutbox

log = logging.getLogger("fusion.gymkhana.notify")
CLAIM_TIMEOUT = timedelta(minutes=10)


def deliver_pending(*, limit: int = 500) -> dict[str, int]:
    now = timezone.now()
    NotificationOutbox.objects.filter(
        status=NotificationOutbox.Status.SENDING,
        claimed_at__lt=now - CLAIM_TIMEOUT,
    ).update(status=NotificationOutbox.Status.PENDING, claimed_at=None)

    pending = list(
        NotificationOutbox.objects.filter(status=NotificationOutbox.Status.PENDING)
        .order_by("created_at")[:limit]
    )
    if not pending:
        return {"sent": 0, "failed": 0, "deferred": 0}
    emails = {
        user_id: person.email
        for user_id, person in directory.get_users(
            list({row.recipient_user_id for row in pending})
        ).items()
    }

    report = {"sent": 0, "failed": 0, "deferred": 0}
    for row in pending:
        claimed = NotificationOutbox.objects.filter(
            pk=row.pk, status=NotificationOutbox.Status.PENDING,
        ).update(status=NotificationOutbox.Status.SENDING, claimed_at=now)
        if not claimed:
            report["deferred"] += 1
            continue
        address = emails.get(row.recipient_user_id, "")
        try:
            if not address:
                raise ValueError("The recipient has no email address in the directory.")
            send_mail(
                subject=row.subject,
                message=row.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[address],
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001
            row.status = NotificationOutbox.Status.FAILED
            row.attempts += 1
            row.last_error = f"{exc.__class__.__name__}: {exc}"[:300]
            row.claimed_at = None
            row.save(update_fields=[
                "status", "attempts", "last_error", "claimed_at", "updated_at",
            ])
            log.error("gymkhana.notify.failed id=%s error=%s", row.pk, row.last_error)
            report["failed"] += 1
            continue
        row.status = NotificationOutbox.Status.SENT
        row.sent_at = timezone.now()
        row.claimed_at = None
        row.save(update_fields=["status", "sent_at", "claimed_at", "updated_at"])
        report["sent"] += 1
    return report


@transaction.atomic
def retry_failed() -> int:
    return NotificationOutbox.objects.filter(
        status=NotificationOutbox.Status.FAILED,
    ).update(status=NotificationOutbox.Status.PENDING, last_error="", claimed_at=None)
