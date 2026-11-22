from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.hr.models import Claim, HRNotification, LeaveRequest, WorkflowRoute
from modules.hr.services.common import audit
from modules.hr.services.notifications import enqueue

log = logging.getLogger("fusion.hr.notifications")


@shared_task(name="hr.deliver_notifications")
def deliver_notifications(limit: int = 500) -> dict[str, int]:
    pending = list(
        HRNotification.objects.filter(email_status="pending").order_by("created_at")[
            : max(1, min(limit, 500))
        ]
    )
    people = directory.get_users([row.recipient_user_id for row in pending])
    sent = failed = deferred = 0

    for row in pending:
        claimed = HRNotification.objects.filter(pk=row.pk, email_status="pending").update(
            email_status="sending"
        )
        if not claimed:
            deferred += 1
            continue
        person = people.get(row.recipient_user_id)
        if person is None or not person.email:
            HRNotification.objects.filter(pk=row.pk, email_status="sending").update(
                email_status="failed",
                email_attempts=row.email_attempts + 1,
                email_error="No official email address is available.",
            )
            failed += 1
            continue
        try:
            sent_messages = send_mail(
                subject=row.subject,
                message=row.body,
                from_email=None,
                recipient_list=[person.email],
                fail_silently=False,
            )
        except (OSError, smtplib.SMTPException) as exc:
            log.error(
                "hr.notification.email_failed id=%s error_type=%s", row.pk, type(exc).__name__
            )
            HRNotification.objects.filter(pk=row.pk, email_status="sending").update(
                email_status="failed",
                email_attempts=row.email_attempts + 1,
                email_error=type(exc).__name__,
            )
            failed += 1
            continue
        if sent_messages != 1:
            error_type = "EmailBackendRejectedMessage"
            log.error("hr.notification.email_failed id=%s error_type=%s", row.pk, error_type)
            HRNotification.objects.filter(pk=row.pk, email_status="sending").update(
                email_status="failed",
                email_attempts=row.email_attempts + 1,
                email_error=error_type,
            )
            failed += 1
            continue

        HRNotification.objects.filter(pk=row.pk, email_status="sending").update(
            email_status="sent",
            email_attempts=row.email_attempts + 1,
            email_error="",
            emailed_at=timezone.now(),
        )
        sent += 1
    return {"sent": sent, "failed": failed, "deferred": deferred}


@shared_task(name="hr.generate_pending_reminders")
def generate_pending_reminders(now_iso: str | None = None) -> int:
    now = datetime.fromisoformat(now_iso) if now_iso else timezone.now()
    routes = {
        (route.employee_category, route.request_type): route
        for route in WorkflowRoute.objects.exclude(reminder_after_hours__isnull=True)
    }
    created = 0
    claims = Claim.objects.filter(
        status__in=("pending_authority", "pending_next_authority"),
        current_authority_user_id__isnull=False,
    )
    for claim in claims.iterator():
        route = routes.get((claim.employee_category, claim.request_type))
        if route is None or route.reminder_after_hours is None:
            continue
        if claim.updated_at > now - timedelta(hours=route.reminder_after_hours):
            continue
        notification = enqueue(
            recipient_user_id=claim.current_authority_user_id,
            topic="claim.pending_reminder",
            dedupe_key=(
                f"claim:{claim.pk}:reminder:{claim.authority_step}:{claim.updated_at.isoformat()}"
            ),
            subject="HR claim awaiting your action",
            body=f"A {claim.get_request_type_display()} claim is still awaiting your decision.",
            payload={"claim_id": claim.pk, "status": claim.status},
        )
        if notification is not None:
            with transaction.atomic():
                audit(
                    actor=None,
                    entity_type="claim",
                    entity_id=claim.pk,
                    action="claim.reminder_generated",
                    details={"recipient_user_id": claim.current_authority_user_id},
                )
            created += 1

    leave_requests = LeaveRequest.objects.filter(
        status__in=("pending_authority", "pending_next_authority"),
        current_authority_user_id__isnull=False,
    ).select_related("employee")
    for leave_request in leave_requests.iterator():
        request_type = f"leave_{leave_request.leave_type}"
        route = routes.get((leave_request.employee.employee_category, request_type))
        if route is None or route.reminder_after_hours is None:
            continue
        if leave_request.updated_at > now - timedelta(hours=route.reminder_after_hours):
            continue
        notification = enqueue(
            recipient_user_id=leave_request.current_authority_user_id,
            topic="leave.pending_reminder",
            dedupe_key=(
                f"leave:{leave_request.pk}:reminder:{leave_request.authority_step}:"
                f"{leave_request.updated_at.isoformat()}"
            ),
            subject="Leave request awaiting your action",
            body="A leave request is still awaiting your decision.",
            payload={"leave_request_id": leave_request.pk, "status": leave_request.status},
        )
        if notification is not None:
            with transaction.atomic():
                audit(
                    actor=None,
                    entity_type="leave_request",
                    entity_id=leave_request.pk,
                    action="leave.reminder_generated",
                    details={"recipient_user_id": leave_request.current_authority_user_id},
                )
            created += 1

    return created
