"""Transactional ELM notices and an idempotent email outbox worker."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.leave.models import LeaveNotificationOutbox

log = logging.getLogger("fusion.leave.notify")


def enqueue(*, recipient_user_id: int, topic: str, dedupe_key: str,
            subject: str, body: str, payload: dict | None = None):
    return LeaveNotificationOutbox.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={"recipient_user_id": recipient_user_id, "subject": subject,
                  "body": body, "payload": {**(payload or {}), "topic": topic}},
    )[0]


def enqueue_task(task):
    if task.assigned_user_id is None:
        return None
    req = task.request
    return enqueue(
        recipient_user_id=task.assigned_user_id, topic="task.assigned",
        dedupe_key=f"task:{task.pk}:assigned",
        subject="ELM action required",
        body=(f"Leave request #{req.pk} ({req.category_id}, {req.start_date} to {req.end_date}) "
              f"is waiting for your {task.role.replace('_', ' ')} action."),
        payload={"task_id": task.pk, "request_id": req.pk, "role": task.role},
    )


def enqueue_decision(request, *, decision: str):
    return enqueue(
        recipient_user_id=request.employee_id, topic="request.decision",
        dedupe_key=f"request:{request.pk}:decision:{decision}",
        subject=f"Leave request #{request.pk}: {decision.replace('_', ' ')}",
        body=(f"Your {request.category_id} leave request from {request.start_date} to {request.end_date} "
              f"was {decision.replace('_', ' ')}."),
        payload={"request_id": request.pk, "decision": decision},
    )


def deliver_pending(*, limit: int = 100) -> dict[str, int]:
    now = timezone.now()
    LeaveNotificationOutbox.objects.filter(
        state=LeaveNotificationOutbox.State.SENDING,
        updated_at__lt=now - timedelta(minutes=10),
    ).update(state=LeaveNotificationOutbox.State.PENDING, claimed_at=None)
    pending = list(LeaveNotificationOutbox.objects.filter(state=LeaveNotificationOutbox.State.PENDING)
                   .order_by("created_at")[:limit])
    recipients = directory.get_users([row.recipient_user_id for row in pending])
    report = {"sent": 0, "failed": 0, "deferred": 0}
    for row in pending:
        claimed = LeaveNotificationOutbox.objects.filter(pk=row.pk, state=LeaveNotificationOutbox.State.PENDING).update(
            state=LeaveNotificationOutbox.State.SENDING, claimed_at=now, updated_at=now)
        if not claimed:
            report["deferred"] += 1
            continue
        user = recipients.get(row.recipient_user_id)
        try:
            if not user or not user.email:
                raise ValueError("Recipient has no email address in the institute directory")
            send_mail(row.subject, row.body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        except Exception as exc:  # delivery failure must not roll back the business action
            failed_state = (LeaveNotificationOutbox.State.PENDING if row.attempts < 4
                            else LeaveNotificationOutbox.State.FAILED)
            LeaveNotificationOutbox.objects.filter(pk=row.pk).update(
                state=failed_state, claimed_at=None,
                attempts=row.attempts + 1, last_error=f"{type(exc).__name__}: {exc}"[:300],
                updated_at=timezone.now(),
            )
            report["failed"] += 1
            log.exception("ELM notification delivery failed", extra={"notification_id": row.pk})
        else:
            LeaveNotificationOutbox.objects.filter(pk=row.pk).update(
                state=LeaveNotificationOutbox.State.SENT,
                attempts=row.attempts + 1, claimed_at=None, sent_at=timezone.now(), updated_at=timezone.now(),
            )
            report["sent"] += 1
    return report
