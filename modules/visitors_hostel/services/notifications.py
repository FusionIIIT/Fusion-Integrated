"""Transactional notification outbox for VHMS events."""
from django.db import IntegrityError, transaction
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from modules.visitors_hostel.models import NotificationOutbox

TOPICS = {
    "booking.submitted", "booking.decided", "booking.modified",
    "booking.cancelled", "stay.reminder", "stay.no_show", "stay.overstay",
    "inventory.threshold",
}


def enqueue(*, topic, dedupe_key, subject, body, user_id=None, email="", payload=None):
    if topic not in TOPICS:
        raise ValueError(f"Unknown VHMS notification topic: {topic}")
    if user_id is None and not email:
        raise ValueError("A notification requires a recipient.")
    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic, dedupe_key=dedupe_key,
                recipient_user_id=user_id, recipient_email=email,
                subject=subject, body=body, payload=payload or {})
    except IntegrityError:
        return None


def deliver_pending(*, limit=100):
    """Deliver queued email through Fusion's configured Django email backend."""
    from modules.directory import contracts as directory

    sent = failed = 0
    with transaction.atomic():
        rows = list(NotificationOutbox.objects.select_for_update(skip_locked=True)
                    .filter(status="pending").order_by("created_at")[:limit])
        ids = {r.recipient_user_id for r in rows
               if r.recipient_user_id and not r.recipient_email}
        people = directory.get_users(sorted(ids)) if ids else {}
        for row in rows:
            recipient = row.recipient_email
            if not recipient and row.recipient_user_id in people:
                recipient = people[row.recipient_user_id].email
            try:
                if not recipient:
                    raise ValueError("No email address is available for the recipient.")
                send_mail(row.subject, row.body,
                          getattr(settings, "DEFAULT_FROM_EMAIL", ""),
                          [recipient], fail_silently=False)
                row.status = "sent"
                row.sent_at = timezone.now()
                row.last_error = ""
                sent += 1
            except Exception as exc:  # a failed delivery remains auditable
                row.attempts += 1
                row.status = "failed"
                row.last_error = f"{exc.__class__.__name__}: {exc}"[:300]
                failed += 1
            row.save(update_fields=["status", "sent_at", "attempts", "last_error"])
    return {"sent": sent, "failed": failed}
