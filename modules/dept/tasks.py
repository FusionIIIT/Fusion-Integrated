import logging
import smtplib

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from modules.dept.models import Notification
from modules.directory.contracts import get_users

logger = logging.getLogger(__name__)


@shared_task
def deliver_notification_email():
    ids = list(
        Notification.objects.filter(email_sent_at__isnull=True)
        .exclude(email_attempts__gte=5)
        .order_by("created_at")
        .values_list("id", flat=True)[:100]
    )
    recipients = {n.recipient_user_id for n in Notification.objects.filter(pk__in=ids)}
    identities = get_users(recipients)
    for notification_id in ids:
        with transaction.atomic():
            notification = (
                Notification.objects.select_for_update()
                .filter(pk=notification_id, email_sent_at__isnull=True)
                .first()
            )
            if notification is None:
                continue
            identity = identities.get(notification.recipient_user_id)
            if identity is None or not identity.email:
                notification.email_attempts = 5
                notification.save(update_fields=["email_attempts", "updated_at"])
                continue
            try:
                sent = send_mail(
                    notification.subject,
                    notification.body,
                    None,
                    [identity.email],
                    fail_silently=False,
                )
            except (OSError, smtplib.SMTPException):
                notification.email_attempts += 1
                notification.save(update_fields=["email_attempts", "updated_at"])
                logger.warning(
                    "dept.notification.email_failed notification_id=%s attempt=%s",
                    notification.pk,
                    notification.email_attempts,
                )
                continue
            if sent:
                notification.email_sent_at = timezone.now()
            else:
                notification.email_attempts += 1
            notification.save(update_fields=["email_sent_at", "email_attempts", "updated_at"])
