"""Notification delivery for ELM (BR-EL-035, and the outbound half of
BR-EL-032 / BR-EL-033).

Messages are composed in `domain/notifications.py` and written here. Writes go
through `bulk_create` wherever more than one recipient is involved, because
these calls sit inside workflow transitions that already hold a row lock --
a per-recipient INSERT loop would widen that window for no reason.
"""
from __future__ import annotations

from collections.abc import Iterable

from modules.elm.domain.notifications import (
    NotificationKind,
    NotificationMessage,
    compose_assignment,
)
from modules.elm.models import Notification


def _row(message: NotificationMessage, task_id: int | None) -> Notification:
    return Notification(
        recipient_id=message.recipient_id,
        kind=message.kind.value if isinstance(message.kind, NotificationKind) else str(message.kind),
        subject=message.subject,
        body=message.body,
        link=message.link,
        task_kind=message.task_kind,
        task_id=task_id,
    )


def deliver(message: NotificationMessage, task_id: int | None = None) -> Notification:
    """Persist a single composed notification."""
    row = _row(message, task_id)
    row.save()
    return row


def deliver_many(
    messages: Iterable[NotificationMessage],
    task_id: int | None = None,
) -> list[Notification]:
    """Persist several composed notifications in one round trip."""
    rows = [_row(m, task_id) for m in messages]
    if not rows:
        return []
    return Notification.objects.bulk_create(rows)


def notify_task_assigned(
    recipient_id: int,
    task_kind: str,
    application_ref: str = "",
    applicant_name: str = "",
    task_id: int | None = None,
) -> Notification | None:
    """BR-EL-035 / AFR-EL-030.1: notify the assignee of a new actionable task.

    Returns None when there is no assignee to notify. A stage with no human
    owner yet (an application sitting at a queue nobody is named on) is a
    normal intermediate state, not an error, so this must not raise inside the
    enclosing transaction.
    """
    if not recipient_id:
        return None
    message = compose_assignment(
        recipient_id=recipient_id,
        task_kind=task_kind,
        application_ref=application_ref,
        applicant_name=applicant_name,
    )
    return deliver(message, task_id=task_id)


def mark_read(notification_id: int, recipient_id: int) -> int:
    """Mark one notification read, scoped to its own recipient.

    Scoping the UPDATE by `recipient_id` rather than fetching and checking is
    what stops one user marking another user's notification read (BR-EL-036).
    """
    from django.utils import timezone

    return (
        Notification.objects.filter(id=notification_id, recipient_id=recipient_id, read_at__isnull=True)
        .update(read_at=timezone.now())
    )


def application_ref(application) -> str:
    """Short human reference for an application, used in message bodies."""
    if application is None:
        return ""
    try:
        code = application.leave_type.code
    except Exception:  # noqa: BLE001 - leave_type may not be selected
        code = "leave"
    return f"{code} request #{application.id} ({application.start_date} to {application.end_date})"
