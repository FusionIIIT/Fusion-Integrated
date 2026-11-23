"""Outbox writes (inside the event's transaction) and delivery (AFR-DEPT-041..046)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from modules.department.domain.roles import FACULTY, STUDENT, normalise_department
from modules.department.models import DepartmentNotification
from modules.directory import contracts as directory

log = logging.getLogger("fusion.department.notify")

TOPICS = frozenset(
    {
        "stock_request.created",
        "stock_request.pending_hod",
        "stock_request.issued",
        "stock_request.rejected",
        "feedback.created",
        "feedback.disposed",
        "announcement.published",
        "role.effective",
    }
)

# How a department code is spelled as a student discipline acronym.
_DISCIPLINE = {
    "CSE": "CSE",
    "ECE": "ECE",
    "ME": "ME",
    "Design": "Des.",
    "NS": "NS",
    "SM": "SM",
    "LA": "LA",
}

CLAIM_TIMEOUT = timedelta(minutes=10)
SUBJECT_MAX = DepartmentNotification._meta.get_field("subject").max_length


_ADDRESS = re.compile(r"[^\s<>'\"(),;]+@[^\s<>'\"(),;]+")


def _without_addresses(text: str) -> str:
    """A mail error can name the recipient; the stored error never keeps an address."""
    return _ADDRESS.sub("[address]", text)


def enqueue(*, topic: str, recipients, key: str, subject: str, body: str) -> int:
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    # The subject is built from user text (a title, an item name) and must fit its column.
    subject = subject if len(subject) <= SUBJECT_MAX else subject[: SUBJECT_MAX - 1] + "…"
    rows = [
        DepartmentNotification(
            topic=topic,
            recipient_user_id=uid,
            dedupe_key=f"{topic}:{key}:{uid}",
            subject=subject,
            body=body,
        )
        for uid in sorted({u for u in recipients if u is not None})
    ]
    created = DepartmentNotification.objects.bulk_create(rows, ignore_conflicts=True)
    return len(created)


def announcement_audience(
    *, department_code: str, audience_role: str, programme: str, batch_year: int | None
) -> list[int]:
    """AFR-DEPT-046 with Q10: matching Students and Faculty of the department."""
    recipients: list[int] = []
    if audience_role in (STUDENT, "all"):
        discipline = _DISCIPLINE.get(department_code)
        ids = directory.user_ids_in_discipline(discipline) if discipline else []
        users = directory.get_users(ids)
        recipients += [
            u.user_id
            for u in users.values()
            if (not programme or u.programme == programme)
            and (batch_year is None or u.batch_year == batch_year)
        ]
    if audience_role in (FACULTY, "all"):
        recipients += [
            u.user_id
            for u in directory.get_employees()
            if u.kind == FACULTY and normalise_department(u.department) == department_code
        ]
    return recipients


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    reclaimed: int = 0

    def __str__(self) -> str:
        return f"sent={self.sent} failed={self.failed} reclaimed={self.reclaimed}"


def _send(row: DepartmentNotification, address: str) -> None:
    if not address:
        raise ValueError("recipient has no email address")
    send_mail(row.subject, row.body, settings.DEFAULT_FROM_EMAIL, [address])


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    """Safe to run twice at once: a conditional UPDATE decides who sends each row."""
    now = now or timezone.now()
    report = DeliveryReport()
    report.reclaimed = DepartmentNotification.objects.filter(
        status=DepartmentNotification.SENDING, claimed_at__lt=now - CLAIM_TIMEOUT
    ).update(status=DepartmentNotification.PENDING, claimed_at=None)
    limit = limit or settings.NOTIFY_MAX_PER_RUN
    max_attempts = settings.NOTIFY_MAX_ATTEMPTS
    queue = list(
        DepartmentNotification.objects.filter(status=DepartmentNotification.PENDING).order_by(
            "created_at"
        )[:limit]
    )
    users = directory.get_users([r.recipient_user_id for r in queue])
    for row in queue:
        claimed = DepartmentNotification.objects.filter(
            Q(pk=row.pk) & Q(status=DepartmentNotification.PENDING)
        ).update(status=DepartmentNotification.SENDING, claimed_at=now)
        if not claimed:
            continue
        address = getattr(users.get(row.recipient_user_id), "email", "")
        try:
            _send(row, address)
        except Exception as exc:  # noqa: BLE001  any mail failure is recorded on the row and retried
            attempts = row.attempts + 1
            DepartmentNotification.objects.filter(pk=row.pk).update(
                status=(
                    DepartmentNotification.FAILED
                    if attempts >= max_attempts
                    else DepartmentNotification.PENDING
                ),
                attempts=attempts,
                last_error=_without_addresses(str(exc))[:300],
                claimed_at=None,
            )
            log.warning("department.notify.failed id=%s attempts=%s", row.pk, attempts)
            report.failed += 1
            continue
        DepartmentNotification.objects.filter(pk=row.pk).update(
            status=DepartmentNotification.SENT, sent_at=now, attempts=row.attempts + 1
        )
        report.sent += 1
    return report
