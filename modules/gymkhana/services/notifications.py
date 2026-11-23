"""Notification decisions and delivery (AFR-GYM-013, AFR-GYM-015, AFR-GYM-025)."""

from __future__ import annotations

import logging
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.directory.contracts import get_users
from modules.gymkhana.domain.constants import (
    MEMBERSHIP_STATUS_CONFIRMED,
    NOTIFICATION_FAILED,
    NOTIFICATION_PENDING,
    NOTIFICATION_SENDING,
    NOTIFICATION_SENT,
)
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.notification import GymkhanaNotification
from modules.gymkhana.models.poll import PollTargetGroup
from modules.gymkhana.selectors.people import students_in_groups

log = logging.getLogger("fusion.gymkhana.notify")

TOPIC_SESSION = "session.booked"
TOPIC_EVENT = "event.booked"
TOPIC_POLL = "poll.created"

# A row unresolved this long belonged to a worker that died, and returns to the queue.
CLAIM_TIMEOUT = timedelta(minutes=10)


def announce_booking(booking) -> None:
    """Queue the announcement for the club's members (AFR-GYM-013, AFR-GYM-015)."""
    topic = TOPIC_EVENT if booking.booking_type == "event" else TOPIC_SESSION
    _announce(
        topic=topic,
        dedupe_key=f"booking:{booking.pk}",
        audience={"members_of": booking.club_id},
        subject=f"New {booking.booking_type}: {booking.name}",
        body=(
            f"{booking.club.name} has booked {booking.name} at {booking.venue} on "
            f"{booking.booking_date:%d %b %Y}, {booking.start_time:%H:%M} to "
            f"{booking.end_time:%H:%M}."
        ),
    )


def announce_poll(poll) -> None:
    """Queue the announcement for the targeted groups (AFR-GYM-025, BR-GYM-013)."""
    _announce(
        topic=TOPIC_POLL,
        dedupe_key=f"poll:{poll.pk}",
        audience={"targets_of": poll.pk},
        subject=f"New poll: {poll.title}",
        body=(
            f"{poll.club.name} has opened a poll: {poll.title}. "
            f"Vote before {timezone.localtime(poll.expires_at):%d %b %Y %H:%M}."
        ),
    )


def _announce(*, topic: str, dedupe_key: str, audience: dict, subject: str, body: str) -> None:
    GymkhanaNotification.objects.create(
        topic=topic, dedupe_key=dedupe_key, audience=audience, subject=subject, body=body
    )


def _recipients(audience: dict) -> list[int]:
    if "members_of" in audience:
        return sorted(
            ClubMembership.objects.filter(
                club_id=audience["members_of"], status=MEMBERSHIP_STATUS_CONFIRMED
            ).values_list("student_id", flat=True)
        )
    groups = PollTargetGroup.objects.filter(poll_id=audience["targets_of"])
    return students_in_groups(list(groups.values_list("batch", "branch")))


def deliver_pending(limit: int | None = None) -> int:
    """Expand announcements and send what is due; safe to repeat and to run twice at once."""
    now = timezone.now()
    GymkhanaNotification.objects.filter(
        status=NOTIFICATION_SENDING, claimed_at__lt=now - CLAIM_TIMEOUT
    ).update(status=NOTIFICATION_PENDING, claimed_at=None)
    limit = limit or settings.NOTIFY_MAX_PER_RUN

    for row in _due(now, limit, announcements=True):
        _expand(row)
    rows = _due(now, limit, announcements=False)
    addresses = {
        uid: user.email for uid, user in get_users([r.recipient_user_id for r in rows]).items()
    }
    return sum(_send(row, addresses.get(row.recipient_user_id, "")) for row in rows)


def _due(now, limit: int, *, announcements: bool) -> list[GymkhanaNotification]:
    rows = GymkhanaNotification.objects.filter(
        status=NOTIFICATION_PENDING, recipient_user_id__isnull=announcements
    ).order_by("created_at", "id")[:limit]
    # 1, 2, 4, 8 minutes between attempts, so a dead address stops filling the log.
    return [
        r
        for r in rows
        if r.attempts == 0 or now - r.updated_at >= timedelta(minutes=2 ** (r.attempts - 1))
    ]


def _expand(row: GymkhanaNotification) -> None:
    """Turn one announcement into one row per recipient, once."""
    try:
        recipients = _recipients(row.audience)
    except IamUnavailable as exc:
        _fail(row, str(exc))
        return
    with transaction.atomic():
        claimed = (
            GymkhanaNotification.objects.select_for_update()
            .filter(pk=row.pk, status=NOTIFICATION_PENDING)
            .first()
        )
        if claimed is None:
            return
        GymkhanaNotification.objects.bulk_create(
            [
                GymkhanaNotification(
                    topic=row.topic,
                    dedupe_key=f"{row.dedupe_key}:u{uid}",
                    recipient_user_id=uid,
                    subject=row.subject,
                    body=row.body,
                )
                for uid in recipients
            ],
            ignore_conflicts=True,
        )
        claimed.status = NOTIFICATION_SENT
        claimed.sent_at = timezone.now()
        claimed.save(update_fields=["status", "sent_at", "updated_at"])
    log.info("gymkhana.notify.expanded id=%s recipients=%d", row.pk, len(recipients))


def _send(row: GymkhanaNotification, address: str) -> int:
    # Claimed before sending, so two workers can never both deliver it.
    claimed = GymkhanaNotification.objects.filter(
        pk=row.pk, status=NOTIFICATION_PENDING
    ).update(status=NOTIFICATION_SENDING, claimed_at=timezone.now())
    if not claimed:
        return 0
    if not address:
        _fail(row, "No email address on record for this recipient.")
        return 0
    try:
        send_mail(
            subject=row.subject,
            message=row.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[address],
            fail_silently=False,
        )
    except (SMTPException, OSError) as exc:
        _fail(row, f"{exc.__class__.__name__}: {exc}")
        return 0
    row.status, row.sent_at, row.claimed_at = NOTIFICATION_SENT, timezone.now(), None
    row.save(update_fields=["status", "sent_at", "claimed_at", "updated_at"])
    return 1


def _fail(row: GymkhanaNotification, error: str) -> None:
    row.attempts += 1
    row.last_error = error[:300]
    row.claimed_at = None
    row.status = NOTIFICATION_PENDING
    if row.attempts >= settings.NOTIFY_MAX_ATTEMPTS:
        row.status = NOTIFICATION_FAILED
        log.warning("gymkhana.notify.giving_up id=%s topic=%s", row.pk, row.topic)
    row.save(update_fields=["attempts", "last_error", "claimed_at", "status", "updated_at"])
