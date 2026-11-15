import logging
import smtplib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.directory import contracts as directory
from modules.spacs.models import NotificationOutbox
from modules.spacs.services.contracts import configured_role_holder_resolver
from modules.spacs.services.errors import IntegrationUnavailableError

log = logging.getLogger("fusion.spacs.notifications")
CLAIM_TIMEOUT = timedelta(minutes=10)


@dataclass(frozen=True)
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return f"sent={self.sent} failed={self.failed} deferred={self.deferred}"


def _email_for(row: NotificationOutbox) -> str:
    if row.recipient_user_id is not None:
        user = directory.get_users([row.recipient_user_id]).get(row.recipient_user_id)
    elif row.recipient_role:
        resolver = configured_role_holder_resolver()
        holder_id = resolver.current_holder(row.recipient_role)
        if holder_id is None:
            raise IntegrationUnavailableError(
                f"No current holder is available for role {row.recipient_role!r}."
            )
        user = directory.get_users([holder_id]).get(holder_id)
    else:
        raise IntegrationUnavailableError("SPACS email outbox row has no user or role recipient.")
    if user is None or not user.email:
        raise IntegrationUnavailableError(
            "No email address is available for a SPACS notification recipient."
        )
    return user.email


def _reclaim_stranded(now) -> int:
    return NotificationOutbox.objects.filter(
        channel="email",
        status="sending",
        claimed_at__lt=now - CLAIM_TIMEOUT,
    ).update(status="pending", claimed_at=None)


def _claim(row: NotificationOutbox) -> bool:
    return (
        NotificationOutbox.objects.filter(
            pk=row.pk,
            channel="email",
            status="pending",
        ).update(status="sending", claimed_at=timezone.now())
        == 1
    )


def _mark_failed(
    *,
    row: NotificationOutbox,
    error: str,
    max_attempts: int,
) -> None:
    row.attempts += 1
    row.last_error = error[:500]
    row.claimed_at = None
    row.status = "failed" if row.attempts >= max_attempts else "pending"
    row.save(
        update_fields=[
            "attempts",
            "last_error",
            "claimed_at",
            "status",
            "updated_at",
        ]
    )


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    now = now or timezone.now()
    _reclaim_stranded(now)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    batch_size = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    sent = failed = deferred = 0

    rows = NotificationOutbox.objects.filter(
        channel="email",
        status="pending",
    ).order_by("created_at")[:batch_size]
    for row in rows:
        if row.attempts:
            delay = timedelta(minutes=2 ** min(row.attempts - 1, 10))
            if now - row.updated_at < delay:
                deferred += 1
                continue
        try:
            recipient = _email_for(row)
        except IntegrationUnavailableError as error:
            deferred += 1
            log.warning(
                "spacs.notify.recipient_unavailable id=%s error=%s",
                row.pk,
                error,
            )
            continue
        if not row.subject.strip() or not row.body.strip():
            _mark_failed(
                row=row,
                error="Notification subject and body are required.",
                max_attempts=max_attempts,
            )
            failed += 1
            continue
        if not _claim(row):
            deferred += 1
            continue
        try:
            delivered = send_mail(
                subject=row.subject,
                message=row.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except (OSError, smtplib.SMTPException) as error:
            _mark_failed(
                row=row,
                error=f"{type(error).__name__}: {error}",
                max_attempts=max_attempts,
            )
            failed += 1
            log.warning(
                "spacs.notify.delivery_failed id=%s attempt=%s",
                row.pk,
                row.attempts,
            )
            continue
        if delivered != 1:
            _mark_failed(
                row=row,
                error="The configured email backend did not confirm delivery.",
                max_attempts=max_attempts,
            )
            failed += 1
            continue
        NotificationOutbox.objects.filter(
            pk=row.pk,
            status="sending",
        ).update(
            status="sent",
            sent_at=timezone.now(),
            attempts=row.attempts + 1,
            last_error="",
            claimed_at=None,
        )
        sent += 1

    return DeliveryReport(sent=sent, failed=failed, deferred=deferred)


def inbox_for_user(
    *,
    user_id: int,
    recipient_roles: Sequence[str] = (),
):
    return (
        NotificationOutbox.objects.filter(
            channel="in_dashboard",
        )
        .filter(Q(recipient_user_id=user_id) | Q(recipient_role__in=recipient_roles))
        .order_by("-created_at", "-pk")
    )


@transaction.atomic
def mark_inbox_read(
    *,
    notification_id: int,
    user_id: int,
    recipient_roles: Sequence[str] = (),
) -> NotificationOutbox:
    row = (
        NotificationOutbox.objects.select_for_update()
        .filter(
            pk=notification_id,
            channel="in_dashboard",
        )
        .filter(Q(recipient_user_id=user_id) | Q(recipient_role__in=recipient_roles))
        .first()
    )
    if row is None:
        raise NotFoundError("No such notification.")
    if row.read_at is None:
        row.read_at = timezone.now()
        row.save(update_fields=["read_at"])
    return row
