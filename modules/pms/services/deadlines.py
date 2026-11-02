"""PMS Deadline calculation, monitoring, alerts, and escalation service (CFR-PMS-021)."""

from __future__ import annotations

import datetime
from datetime import timedelta

from django.utils import timezone

from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import OfficeAction, PatentApplication
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def add_business_days(start_date: datetime.datetime, days: int) -> datetime.datetime:
    """Add a specified number of business days (Mon-Fri) to a timestamp."""
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday to Friday
            added += 1
    return current


def calculate_review_deadline(assigned_at: datetime.datetime) -> datetime.datetime:
    """Director review must be completed within 15 business days of assignment (BR-PMS-031)."""
    return add_business_days(assigned_at, 15)


def calculate_revision_deadline(decision_date: datetime.datetime) -> datetime.datetime:
    """A revised application must be resubmitted within 60 calendar days (BR-PMS-035)."""
    return decision_date + timedelta(days=60)


def monitor_and_process_deadlines(now: datetime.datetime | None = None) -> dict[str, int]:
    """Scan active deadlines, issue alerts (30, 15, 5 days), expire overdue revisions, and escalate (BR-PMS-101 to 104)."""
    now = now or timezone.now()
    today = now.date()
    stats = {"alerts_sent": 0, "revisions_expired": 0, "escalations": 0}

    # 1. Overdue revisions -> Expired (BR-PMS-038)
    overdue_revisions = PatentApplication.objects.filter(
        status__in=[
            PatentApplicationStatus.NEEDS_REVISION.value,
            PatentApplicationStatus.REJECTED.value,
        ],
        revision_deadline__lt=now,
    )
    for app in overdue_revisions:
        prev_status = app.status
        app.status = PatentApplicationStatus.EXPIRED.value
        app.save(update_fields=["status", "updated_at"])
        stats["revisions_expired"] += 1

        log_audit(
            application=app,
            action_type="revision_expired",
            from_state=prev_status,
            to_state=app.status,
            details={"reason": "Revision deadline of 60 days exceeded."},
        )
        enqueue_notification(
            topic="application.expired",
            dedupe_key=f"pms:app:expired:{app.id}",
            subject=f"PMS: Patent Application {app.application_no} has expired",
            body=f"Your patent application '{app.title}' has expired due to overdue revision resubmission.",
            recipient_user_id=app.applicant_user_id,
        )

    # 2. Overdue Director Reviews -> Escalate (BR-PMS-104)
    overdue_reviews = PatentApplication.objects.filter(
        status=PatentApplicationStatus.UNDER_REVIEW.value,
        review_deadline__lt=now,
    )
    for app in overdue_reviews:
        stats["escalations"] += 1
        enqueue_notification(
            topic="deadline.escalated",
            dedupe_key=f"pms:app:review_escalated:{app.id}:{today}",
            subject=f"PMS Escalation: Director Review Overdue for {app.application_no}",
            body=f"Review deadline ({app.review_deadline}) for application '{app.title}' has expired. Escalating to PCC_ADMIN.",
            recipient_user_id=app.assigned_director_user_id,
        )

    # 3. Approaching Deadlines -> 30, 15, 5 day alerts (BR-PMS-101, 102, 103)
    active_apps = PatentApplication.objects.filter(
        status__in=[
            PatentApplicationStatus.UNDER_REVIEW.value,
            PatentApplicationStatus.NEEDS_REVISION.value,
        ]
    )
    for app in active_apps:
        target_dl = (
            app.review_deadline
            if app.status == PatentApplicationStatus.UNDER_REVIEW.value
            else app.revision_deadline
        )
        if not target_dl:
            continue

        days_remaining = (target_dl.date() - today).days
        for alert_days in (30, 15, 5):
            if days_remaining == alert_days:
                stats["alerts_sent"] += 1
                topic = f"deadline.alert_{alert_days}"
                recipient = (
                    app.assigned_director_user_id
                    if app.status == PatentApplicationStatus.UNDER_REVIEW.value
                    else app.applicant_user_id
                )
                enqueue_notification(
                    topic=topic,
                    dedupe_key=f"pms:app:deadline_alert:{app.id}:{alert_days}:{today}",
                    subject=f"PMS Alert: {alert_days} days remaining for {app.application_no}",
                    body=f"There are {alert_days} days remaining before the deadline ({target_dl}) for '{app.title}'.",
                    recipient_user_id=recipient,
                )

    # 4. Office Action deadlines (BR-PMS-099, 101, 102, 103, 104)
    active_oas = OfficeAction.objects.filter(
        status__in=["recorded", "awaiting_applicant_approval", "response_ready"]
    ).select_related("application")
    for oa in active_oas:
        days_remaining = (oa.due_date - today).days
        if days_remaining < 0:
            stats["escalations"] += 1
            enqueue_notification(
                topic="deadline.escalated",
                dedupe_key=f"pms:oa:escalated:{oa.id}:{today}",
                subject=f"PMS Escalation: Office Action Response Overdue for {oa.application.application_no}",
                body=f"Office action due date ({oa.due_date}) has passed for '{oa.application.title}'.",
                recipient_user_id=oa.application.assigned_attorney_user_id
                or oa.application.applicant_user_id,
            )
        elif days_remaining in (30, 15, 5):
            stats["alerts_sent"] += 1
            enqueue_notification(
                topic=f"deadline.alert_{days_remaining}",
                dedupe_key=f"pms:oa:alert:{oa.id}:{days_remaining}:{today}",
                subject=f"PMS Alert: {days_remaining} days until Office Action Due Date",
                body=f"Office action response for {oa.application.application_no} is due in {days_remaining} days on {oa.due_date}.",
                recipient_user_id=oa.application.assigned_attorney_user_id
                or oa.application.applicant_user_id,
            )

    return stats
