"""Scheduled deadline and resubmission-period maintenance."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.pms.models import (
    Application,
    ApplicationTransition,
    Deadline,
    PmsAuditEvent,
    PmsConfiguration,
    PmsNotification,
)


def _config(key, default=None):
    row = PmsConfiguration.objects.filter(key=key).first()
    return row.value if row else default


def _notify(*, key, user_id, app, event, subject, body):
    if user_id is None:
        return False
    _, created = PmsNotification.objects.get_or_create(
        dedupe_key=key,
        defaults={
            "recipient_user_id": user_id,
            "application": app,
            "event": event,
            "subject": subject,
            "body": body,
        },
    )
    return created


def process_deadlines(now=None):
    now = now or timezone.now()
    local_today = timezone.localdate(now)
    expired_revisions = 0
    missed_deadlines = 0
    reminders = 0
    intervals = _config("deadline_alert_days", [30, 15, 5])
    escalation_ids = _config("deadline_escalation_user_ids", [])

    ids = list(
        Application.objects.filter(
            status__in=[Application.Status.NEEDS_REVISION, Application.Status.REJECTED],
            revision_due_at__lt=now,
        ).values_list("pk", flat=True)[:500]
    )
    for app_id in ids:
        with transaction.atomic():
            app = Application.objects.select_for_update().get(pk=app_id)
            if (
                app.status not in (Application.Status.NEEDS_REVISION, Application.Status.REJECTED)
                or not app.revision_due_at
                or app.revision_due_at >= now
            ):
                continue
            previous = app.status
            app.status = Application.Status.EXPIRED
            app.save(update_fields=["status", "updated_at"])
            ApplicationTransition.objects.create(
                application=app,
                from_status=previous,
                to_status=app.status,
                actor_user_id=None,
                action="revision_deadline_expired",
            )
            PmsAuditEvent.objects.create(
                actor_user_id=None,
                application=app,
                action="revision_deadline_expired",
                previous_state=previous,
                new_state=app.status,
                metadata={"revision_due_at": app.revision_due_at.isoformat()},
            )
            expired_revisions += 1

    deadlines = Deadline.objects.filter(
        status="open", due_at__lte=now + timedelta(days=max(intervals or [0]))
    )
    for item in deadlines.select_related("application").iterator():
        days_remaining = (item.due_at.date() - local_today).days
        if (
            days_remaining in intervals
            and days_remaining > 0
            and item.responsible_user_id
            and _notify(
                key=f"deadline:{item.pk}:reminder:{days_remaining}",
                user_id=item.responsible_user_id,
                app=item.application,
                event="deadline.reminder",
                subject="PMS deadline reminder",
                body=(
                    f"{item.kind} for {item.application.application_number} is due in "
                    f"{days_remaining} day(s), on {item.due_at.date()}."
                ),
            )
        ):
            reminders += 1
        if item.due_at >= now:
            continue
        with transaction.atomic():
            locked = Deadline.objects.select_for_update().get(pk=item.pk)
            if locked.status != "open" or locked.due_at >= now:
                continue
            locked.status = "escalated" if escalation_ids else "missed"
            locked.save(update_fields=["status"])
            PmsAuditEvent.objects.create(
                actor_user_id=None,
                application=item.application,
                action="deadline_escalated" if escalation_ids else "deadline_missed",
                metadata={
                    "deadline_id": item.pk,
                    "kind": item.kind,
                    "due_at": item.due_at.isoformat(),
                },
            )
            recipients = [item.responsible_user_id, *escalation_ids]
            for recipient in {x for x in recipients if x}:
                _notify(
                    key=f"deadline:{item.pk}:missed:{recipient}",
                    user_id=recipient,
                    app=item.application,
                    event="deadline.missed",
                    subject="PMS deadline missed",
                    body=(
                        f"{item.kind} for {item.application.application_number} was due "
                        f"{item.due_at.date()} and is now {locked.status}."
                    ),
                )
            missed_deadlines += 1
    return {
        "expired_revisions": expired_revisions,
        "missed_deadlines": missed_deadlines,
        "reminders_queued": reminders,
    }
