"""ELM's notification outbox (BR-EL-035).

Assigning an actionable task must notify the assignee; the
platform has no shared notification service yet, so ELM
owns its outbox the same way the placement module does:
services enqueue rows, a Celery task drains them. A
``dedupe_key`` keeps a sweep or a retry from notifying
twice for the same event.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from modules.elm.models import Notification

log = logging.getLogger("fusion.elm.notifications")


def notify(user_id: int, topic: str, subject: str,
             body: str = "", *,
             payload: dict | None = None,
             dedupe_key: str | None = None) -> Notification | None:
    """Enqueue one notification. A duplicate ``dedupe_key``
    is a no-op, not a second row."""
    if dedupe_key and Notification.objects.filter(
            dedupe_key=dedupe_key).exists():
        return None
    return Notification.objects.create(
        recipient_user_id=user_id,
        topic=topic,
        subject=subject,
        body=body,
        payload=payload or {},
        dedupe_key=dedupe_key,
    )


def notify_task_assigned(task) -> None:
    """BR-EL-035: notify the assignee of a new task."""
    request = task.request
    notify(
        task.assignee_user_id,
        "task_assigned",
        f"Leave {task.task_class.replace('_', ' ')}: "
        f"{request.user_id} — {request.category}",
        f"A {task.task_class.replace('_', ' ')} task needs "
        f"your action on a {request.category} leave request "
        f"({request.start_date} → {request.end_date}).",
        payload={"request_id": request.id,
                 "task_id": task.id,
                 "task_class": task.task_class},
        dedupe_key=(
            f"task:{request.id}:{task.task_class}:"
            f"{task.assignee_user_id}:{task.id}"),
    )


def notify_request_outcome(request, outcome: str) -> None:
    notify(
        request.user_id,
        "request_update",
        f"Leave {request.category} {outcome}",
        f"Your {request.category} leave request "
        f"({request.start_date} → {request.end_date}) "
        f"was {outcome}.",
        payload={"request_id": request.id, "outcome": outcome},
        dedupe_key=f"outcome:{request.id}:{outcome}",
    )


# -- delivery ------------------------------------------------------------

#: How long a "sending" row may sit before the sweep
#: assumes the worker died and re-queues it.
CLAIM_TIMEOUT = timedelta(minutes=10)


def deliver_pending(*, limit: int | None = None,
                      now=None) -> dict:
    """Drain the outbox (BR-EL-035).

    Safe to run concurrently and safe to re-run: a
    single conditional UPDATE decides which worker
    owns a row, so two workers never send the same
    notification.
    """
    from django.conf import settings
    from django.core.mail import send_mail

    now = now or timezone.now()
    # Reclaim rows whose worker died mid-send.
    Notification.objects.filter(
        status="sending",
        claimed_at__lt=now - CLAIM_TIMEOUT).update(
            status="pending", claimed_at=None)

    limit = limit or getattr(
        settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(
        settings, "NOTIFY_MAX_ATTEMPTS", 5)
    report = {"sent": 0, "failed": 0,
              "deferred": 0, "no_address": 0}

    from modules.directory import contracts as directory

    pending = list(
        Notification.objects.filter(
            status="pending").order_by("created_at")[:limit])
    ids = {n.recipient_user_id for n in pending}
    try:
        people = directory.get_users(sorted(ids))
    except Exception:                              # noqa: BLE001
        people = {}
    addresses = {uid: p.email
                 for uid, p in people.items() if p.email}

    for row in pending:
        to = addresses.get(row.recipient_user_id, "")
        if not to:
            row.attempts += 1
            row.last_error = (
                "No email address on record for "
                "this recipient.")
            if row.attempts >= max_attempts:
                row.status = "failed"
            row.save()
            report["no_address"] += 1
            continue

        # Claim before sending, never after.
        claimed = Notification.objects.filter(
            pk=row.pk, status="pending").update(
                status="sending",
                claimed_at=timezone.now()) == 1
        if not claimed:
            report["deferred"] += 1
            continue

        try:
            send_mail(
                subject=row.subject, message=row.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to], fail_silently=False,
            )
        except Exception as exc:                   # noqa: BLE001
            row.attempts += 1
            row.last_error = f"{exc.__class__.__name__}: {exc}"[:300]
            if row.attempts >= max_attempts:
                row.status = "failed"
            else:
                row.status = "pending"
            row.claimed_at = None
            row.save()
            report["failed"] += 1
            continue

        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.claimed_at = None
        row.save(update_fields=["status", "sent_at",
                                  "attempts", "last_error",
                                  "claimed_at"])
        report["sent"] += 1

    remaining = Notification.objects.filter(
        status="pending").count()
    if remaining:
        log.info("elm.notify.backlog remaining=%d",
                 remaining)
    return report
