"""Deliver queued ELM notifications outside the request transaction."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from modules.directory.models import UserRef
from modules.elm.models import LeaveNotificationOutbox

log = logging.getLogger("fusion.elm.notify")


def deliver(limit: int = 100) -> dict[str, int]:
    report = {"sent": 0, "failed": 0, "skipped": 0}
    rows = LeaveNotificationOutbox.objects.filter(
        status__in=("pending", "failed"), attempts__lt=5,
    ).order_by("created_at")[:limit]
    for row in rows:
        email = row.recipient_email or UserRef.objects.filter(
            user_id=row.recipient_user_id).values_list("email", flat=True).first()
        if not email:
            row.status = "failed"
            row.attempts += 1
            row.last_error = "Recipient has no email address in the Fusion directory."
            row.save(update_fields=[
                "status", "attempts", "last_error", "updated_at",
            ])
            report["failed"] += 1
            continue
        row.attempts += 1
        try:
            sent = send_mail(
                row.subject, row.body, settings.DEFAULT_FROM_EMAIL, [email],
                fail_silently=False)
            if sent != 1:
                raise RuntimeError("The configured email backend did not accept the message.")
        except Exception as exc:
            row.status = "failed"
            row.last_error = str(exc)[:300]
            row.save(update_fields=[
                "status", "attempts", "last_error", "updated_at",
            ])
            log.exception("elm.notify.delivery_failed outbox_id=%s", row.pk)
            report["failed"] += 1
        else:
            row.status = "sent"
            row.sent_at = timezone.now()
            row.last_error = ""
            row.save(update_fields=[
                "status", "attempts", "sent_at", "last_error", "updated_at",
            ])
            report["sent"] += 1
    return report
