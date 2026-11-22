"""Celery workers for year-end, SLA, notification and resumption work."""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from modules.leave import contracts
from modules.leave.models import LeaveNotification, ResumptionRecord
from modules.leave.services import year_end
from modules.leave.services.sla import process_thresholds

log = logging.getLogger("fusion.leave.tasks")


@shared_task(name="leave.process_year_end", acks_late=True, reject_on_worker_lost=True)
def process_year_end_task(year: int | None = None) -> dict[str, int]:
    closed_year = year if year is not None else timezone.localdate().year - 1
    result = year_end.process_year_end(closed_year)
    log.info(
        "leave.year_end.completed year=%d transactions=%d", closed_year, result["transactions"]
    )
    return result


@shared_task(name="leave.process_sla", acks_late=True, reject_on_worker_lost=True)
def process_sla_task() -> dict[str, int]:
    return process_thresholds()


@shared_task(name="leave.deliver_notifications", acks_late=True, reject_on_worker_lost=True)
def deliver_notifications(limit: int = 200) -> dict[str, int]:
    pending = list(
        LeaveNotification.objects.filter(status="pending").order_by("created_at")[:limit]
    )
    try:
        recipients = contracts.get_employees([row.recipient_user_id for row in pending])
    except Exception as exc:  # noqa: BLE001 - isolate failures of external IAM providers
        log.warning("leave.notify.directory_unavailable error=%s", type(exc).__name__)
        return {"sent": 0, "failed": len(pending)}
    sent = failed = 0
    for row in pending:
        address = recipients.get(row.recipient_user_id)
        if address is None or not address.email:
            row.status = "failed"
            row.last_error = "No employee email is available from IAM."
            row.attempts += 1
            row.save(update_fields=["status", "last_error", "attempts"])
            failed += 1
            continue
        try:
            send_mail(
                row.subject,
                row.body,
                settings.DEFAULT_FROM_EMAIL,
                [address.email],
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001 - mail transports raise varied failures
            row.attempts += 1
            row.last_error = f"{type(exc).__name__}: {exc}"[:300]
            row.status = "failed" if row.attempts >= 5 else "pending"
            row.save(update_fields=["attempts", "last_error", "status"])
            failed += 1
            continue
        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.save(update_fields=["status", "sent_at", "attempts", "last_error"])
        sent += 1
    return {"sent": sent, "failed": failed}


@shared_task(name="leave.synchronize_resumption", acks_late=True, reject_on_worker_lost=True)
def synchronize_resumption(record_id: int) -> str:
    try:
        record = ResumptionRecord.objects.select_related("application").get(pk=record_id)
    except ResumptionRecord.DoesNotExist:
        return "missing"
    try:
        contracts.synchronize_attendance(
            user_id=record.employee_user_id,
            start_date=record.application.start_date,
            end_date=record.actual_resumption_date,
        )
    except contracts.ExternalDependencyUnavailable as exc:
        record.synchronization_status = "pending_external"
        record.synchronization_error = str(exc)[:300]
        record.save(update_fields=["synchronization_status", "synchronization_error"])
        return "pending_external"
    record.synchronization_status = "synchronized"
    record.synchronization_error = ""
    record.save(update_fields=["synchronization_status", "synchronization_error"])
    return "synchronized"
