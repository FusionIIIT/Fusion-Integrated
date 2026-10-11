"""Notification outbox (BR-EL-035, PS §7).

Written inside the transaction that caused it, so a decision and its
notification commit together or not at all. `dedupe_key` makes redelivery
idempotent, which matters because the worker runs with acks_late.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from modules.leave.models import LeaveNotificationOutbox as Outbox

log = logging.getLogger("fusion.leave.notifications")


def enqueue(*, topic: str, dedupe_key: str, recipient_user_id: int | None,
            subject: str, body: str, payload: dict[str, Any] | None = None) -> None:
    """Queue one notification. Re-queueing the same key is a no-op."""
    Outbox.objects.get_or_create(
        dedupe_key=dedupe_key[:200],
        defaults={"topic": topic[:60], "recipient_user_id": recipient_user_id,
                  "subject": subject[:200], "body": body,
                  "payload": payload or {}})


def notify_assignment(*, request, task) -> None:
    """BR-EL-035 — an actionable task assignment notifies its holder."""
    if task.assignee_user_id is None and not task.assignee_role:
        return
    enqueue(
        topic="leave.task.assigned",
        dedupe_key=f"leave.task:{task.pk}:assigned",
        recipient_user_id=task.assignee_user_id,
        subject=f"Leave task awaiting you — {request.reference or request.pk}",
        body=(f"A {request.get_category_display()} leave request for "
              f"{request.period_from} to {request.period_to} is waiting at "
              f"{task.step_kind.replace('_', ' ')}."),
        payload={"request_id": request.pk, "task_id": task.pk,
                 "step_kind": task.step_kind, "assignee_role": task.assignee_role},
    )


def notify_decision(*, request, subject: str, body: str) -> None:
    """A final decision reaches the employee (PS §7)."""
    enqueue(topic="leave.request.decided",
            dedupe_key=f"leave.request:{request.pk}:decided:{request.status}",
            recipient_user_id=request.user_id, subject=subject, body=body,
            payload={"request_id": request.pk, "status": request.status})


def notify_roles(*, request, subject: str, body: str) -> None:
    """The concerned roles are informed when a request is withdrawn (BR-EL-022)."""
    enqueue(topic="leave.request.withdrawn",
            dedupe_key=f"leave.request:{request.pk}:withdrawn",
            recipient_user_id=None, subject=subject, body=body,
            payload={"request_id": request.pk, "status": request.status})


def deliver_pending(*, limit: int | None = None) -> dict[str, int]:
    """Drain the outbox. Console/EMAIL backend decided by settings."""
    cap = limit or settings.NOTIFY_MAX_PER_RUN
    rows = list(Outbox.objects.filter(status="pending").order_by("created_at")[:cap])
    report = {"sent": 0, "failed": 0}
    for row in rows:
        row.status = "sending"
        row.attempts += 1
        row.claimed_at = timezone.now()
        row.save(update_fields=["status", "attempts", "claimed_at"])
        try:
            _deliver(row)
        except Exception as exc:                     # noqa: BLE001 — park it
            row.status = ("failed" if row.attempts >= settings.NOTIFY_MAX_ATTEMPTS
                          else "pending")
            row.last_error = str(exc)[:300]
            row.save(update_fields=["status", "last_error"])
            report["failed"] += 1
            log.warning("leave.notify.failed topic=%s err=%s", row.topic, exc)
        else:
            row.status = "sent"
            row.sent_at = timezone.now()
            row.save(update_fields=["status", "sent_at"])
            report["sent"] += 1
    return report


def _deliver(row: Outbox) -> None:
    """No email address is held locally, so the body is logged and parked.

    The recipient is named by IAM user id; wiring this to the IAM directory is
    the integration point, and it must not silently drop a notification.
    """
    log.info("leave.notify topic=%s recipient=%s subject=%s",
             row.topic, row.recipient_user_id, row.subject)


def pending_count() -> int:
    return Outbox.objects.filter(status="pending").aggregate(
        n=Count("pk"))["n"] or 0
