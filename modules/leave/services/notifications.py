"""Notifications (BR-EL-035, CFR-EL-016, BR-EL-022, BR-EL-032/033), queued with their cause."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory
from modules.leave.models import Outbox

log = logging.getLogger("fusion.leave.notify")

TOPICS = frozenset({"task.assigned", "decision.final", "request.withdrawn",
                    "substitute.declined", "sla.reminder", "sla.escalated"})


def enqueue(*, topic: str, dedupe_key: str, subject: str, body: str,
            user_id: int | None = None, designation: str = "") -> Outbox | None:
    if topic not in TOPICS:
        raise ValueError(f"Unknown leave notification topic {topic!r}.")
    if user_id is None and not designation:
        raise ValueError("A notification needs a person or a designation to reach.")
    try:
        with transaction.atomic():
            return Outbox.objects.create(topic=topic, dedupe_key=dedupe_key[:160],
                                         subject=subject[:200], body=body,
                                         recipient_user_id=user_id,
                                         recipient_designation=designation)
    except IntegrityError:
        return None


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    deferred: int = 0
    undeliverable: int = 0

    def __str__(self) -> str:
        return (f"sent={self.sent} failed={self.failed} deferred={self.deferred} "
                f"undeliverable={self.undeliverable}")


CLAIM_TIMEOUT = timedelta(minutes=10)


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    """Safe to run concurrently: a row is claimed by one conditional UPDATE before it is sent."""
    now = now or timezone.now()
    Outbox.objects.filter(status="sending", claimed_at__lt=now - CLAIM_TIMEOUT).update(
        status="pending", claimed_at=None)
    limit = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    report = DeliveryReport()
    rows = list(Outbox.objects.filter(status="pending").order_by("created_at")[:limit])

    try:
        holders = directory.get_designation_holders(
            sorted({r.recipient_designation for r in rows if r.recipient_designation}))
    except IamUnavailable as exc:
        log.warning("leave.notify.holders_unavailable err=%s", exc)
        holders = None
    people = directory.get_users(sorted(
        {r.recipient_user_id for r in rows if r.recipient_user_id}))

    for row in rows:
        if row.attempts and now - row.updated_at < timedelta(minutes=2 ** (row.attempts - 1)):
            report.deferred += 1
            continue
        if row.recipient_designation:
            if holders is None:
                report.deferred += 1
                continue
            addresses = [p.email for p in holders.get(row.recipient_designation, []) if p.email]
        else:
            person = people.get(row.recipient_user_id)
            addresses = [person.email] if person and person.email else []
        if not addresses:
            row.status = "undeliverable"
            row.last_error = "Nobody with an email address holds this post."[:300]
            row.save(update_fields=["status", "last_error", "updated_at"])
            report.undeliverable += 1
            continue
        if Outbox.objects.filter(pk=row.pk, status="pending").update(
                status="sending", claimed_at=timezone.now()) != 1:
            report.deferred += 1
            continue
        try:
            send_mail(subject=row.subject, message=row.body,
                      from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=addresses,
                      fail_silently=False)
        except Exception as exc:                                   # noqa: BLE001
            row.attempts += 1
            row.last_error = f"{exc.__class__.__name__}: {exc}"[:300]
            row.status = "failed" if row.attempts >= max_attempts else "pending"
            row.claimed_at = None
            row.save(update_fields=["attempts", "last_error", "status", "claimed_at",
                                    "updated_at"])
            report.failed += 1
            continue
        row.status, row.sent_at, row.claimed_at = "sent", timezone.now(), None
        row.attempts += 1
        row.save(update_fields=["status", "sent_at", "claimed_at", "attempts", "updated_at"])
        report.sent += 1
    return report
