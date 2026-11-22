"""Idempotent scheduled notification events for the platform mail dispatcher."""

from datetime import datetime

from celery import shared_task
from django.utils import timezone

from .models import BookingRequest, InventoryItem
from .services import arrival, inventory_alert, queue_notification


@shared_task(name="visitor_hostel.generate_alerts", acks_late=True)
def generate_alerts():
    now = timezone.now()
    for booking in BookingRequest.objects.filter(status__in=["confirmed", "checked_in"]).iterator():
        end = timezone.make_aware(datetime.combine(booking.check_out_date, booking.check_out_time))
        event = None
        if booking.status == "confirmed" and arrival(booking) < now:
            event = "no_show_alert"
        elif booking.status == "checked_in" and end < now:
            event = "overstay_alert"
        elif booking.check_in_date == timezone.localdate(now) and booking.status == "confirmed":
            event = "check_in_reminder"
        elif booking.check_out_date == timezone.localdate(now) and booking.status == "checked_in":
            event = "check_out_reminder"
        if event:
            queue_notification(
                event,
                key=f"{event}:{booking.pk}:{timezone.localdate(now)}",
                booking=booking,
                role="vh_caretaker",
            )
    for item in InventoryItem.objects.all().iterator():
        inventory_alert(item)


@shared_task(
    name="visitor_hostel.deliver_notifications", acks_late=True, soft_time_limit=270, time_limit=300
)
def deliver_notifications():
    """Bounded outbox delivery with backoff; SMTP delivery is at least once."""
    import logging
    import smtplib
    from datetime import timedelta

    from django.db import transaction

    from .models import Notification, RoleAssignment

    logger = logging.getLogger(__name__)
    now = timezone.now()
    ids = list(
        Notification.objects.filter(delivered_at__isnull=True, next_attempt_at__lte=now)
        .order_by("pk")
        .values_list("pk", flat=True)[:100]
    )
    from fusion_auth.client import IamUnavailable
    from modules.directory.contracts import get_users

    requester_ids = list(
        Notification.objects.filter(pk__in=ids, recipient_id__isnull=False).values_list(
            "recipient_id", flat=True
        )
    )
    try:
        requesters = get_users(requester_ids)
    except IamUnavailable:
        logger.warning("IAM unavailable during hostel notification delivery")
        return 0
    delivered = 0
    for notification_id in ids:
        with transaction.atomic():
            event = (
                Notification.objects.select_for_update(skip_locked=True)
                .filter(pk=notification_id)
                .first()
            )
            if event is None or event.delivered_at or event.next_attempt_at > timezone.now():
                continue
            recipients = list(
                RoleAssignment.objects.filter(
                    role=event.recipient_role, starts_at__lte=now, ends_at__gt=now
                ).values_list("email", flat=True)
            )
            requester = requesters.get(event.recipient_id)
            if requester and requester.email:
                recipients.append(requester.email)
            recipients = sorted(set(recipients))
            event.attempts += 1
            try:
                _send_event(event, recipients)
            except (OSError, smtplib.SMTPException, ValueError) as exc:
                event.last_error = type(exc).__name__
                event.next_attempt_at = now + timedelta(
                    seconds=min(3600, 30 * 2 ** min(event.attempts, 7))
                )
                logger.warning(
                    "Hostel notification delivery failed: id=%s error=%s",
                    event.pk,
                    event.last_error,
                )
            else:
                event.delivered_at = timezone.now()
                event.last_error = ""
                delivered += 1
            event.save()
    return delivered


def _send_event(event, recipients):
    from django.conf import settings
    from django.core.mail import send_mail

    if not recipients:
        raise ValueError("No current notification recipient.")
    if (
        send_mail(
            f"Hostel: {event.event.replace('_', ' ')}",
            f"Hostel event {event.key}. Sign in to review the operational record.",
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
        != 1
    ):
        raise ValueError("Mail backend did not accept the message.")
