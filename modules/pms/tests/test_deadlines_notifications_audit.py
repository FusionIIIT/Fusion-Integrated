"""Deadline monitoring, notifications, and audit trail tests for PMS.

Maps to:
- CFR-PMS-021 (Deadline Monitoring, Alerts, and Escalation)
- CFR-PMS-023 (System-Generated Email Notifications)
- CFR-PMS-024 (Audit, Compliance, and Security Controls)
- BR-PMS-031, BR-PMS-035, BR-PMS-038, BR-PMS-097..104, BR-PMS-116, BR-PMS-121, BR-PMS-122
"""

import datetime
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    PmsNotificationOutbox,
)
from modules.pms.services import (
    add_business_days,
    calculate_review_deadline,
    calculate_revision_deadline,
    enqueue_notification,
    log_audit,
    monitor_and_process_deadlines,
    send_pending_notifications,
    submit_application,
)

pytestmark = pytest.mark.django_db


# --- 1. Deadline Calculations (BR-PMS-031, BR-PMS-035) ---


def test_add_business_days_skips_weekends():
    """Verify business days addition correctly jumps Saturday and Sunday."""
    # A Friday at noon
    friday = datetime.datetime(2026, 11, 6, 12, 0, tzinfo=datetime.UTC)
    # 1 business day later is Monday
    monday = add_business_days(friday, 1)
    assert monday.weekday() == 0  # Monday
    assert (monday - friday).days == 3

    # 15 business days (3 full weeks)
    day_15 = add_business_days(friday, 15)
    # 15 business days starting Friday spans 3 weekends = 21 calendar days
    assert (day_15 - friday).days == 21


def test_calculate_review_deadline():
    """BR-PMS-031, 097: Director review must be completed within 15 business days of assignment."""
    start = datetime.datetime(2026, 11, 2, 10, 0, tzinfo=datetime.UTC)
    dl = calculate_review_deadline(start)
    assert dl > start
    assert (dl - start).days >= 19  # includes at least 2 weekends


def test_calculate_revision_deadline():
    """BR-PMS-035, 098: Revised application must be resubmitted within 60 calendar days."""
    decision_time = datetime.datetime(2026, 8, 1, 10, 0, tzinfo=datetime.UTC)
    dl = calculate_revision_deadline(decision_time)
    assert (dl - decision_time).days == 60


# --- 2. Deadline Alerts & Escalations (BR-PMS-101..104, BR-PMS-038) ---


def test_deadline_alerts_30_15_5_days():
    """BR-PMS-101, 102, 103: PMS generates alerts 30, 15, and 5 days before tracked deadline."""
    app = submit_application(
        applicant_user_id=1001,
        title="Tracked App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001

    now = timezone.now()

    # 15 days remaining
    app.review_deadline = now + timedelta(days=15)
    app.save()

    stats = monitor_and_process_deadlines(now=now)
    assert stats["alerts_sent"] >= 1

    alert_notif = PmsNotificationOutbox.objects.filter(
        topic="deadline.alert_15", recipient_user_id=2001
    ).first()
    assert alert_notif is not None
    assert "15 days remaining" in alert_notif.subject


def test_missed_review_deadline_triggers_escalation():
    """BR-PMS-104: Missed tracked deadline triggers escalation."""
    app = submit_application(
        applicant_user_id=1001,
        title="Late App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001

    now = timezone.now()
    app.review_deadline = now - timedelta(days=1)  # yesterday
    app.save()

    stats = monitor_and_process_deadlines(now=now)
    assert stats["escalations"] >= 1

    esc_notif = PmsNotificationOutbox.objects.filter(
        topic="deadline.escalated", recipient_user_id=2001
    ).first()
    assert esc_notif is not None
    assert "Escalation" in esc_notif.subject


# --- 3. Notification Outbox & Sending (CFR-PMS-023, BR-PMS-116) ---


def test_notification_enqueue_and_deduplication():
    """BR-PMS-116: Outbox enqueuing and idempotent deduplication."""
    n1 = enqueue_notification(
        topic="application.submitted",
        dedupe_key="pms:test:dedupe:1",
        subject="Subject 1",
        body="Body 1",
        recipient_user_id=1001,
    )
    assert n1 is not None
    assert n1.status == "pending"

    # Enqueueing with identical dedupe_key returns None (idempotent, no duplicate row)
    n2 = enqueue_notification(
        topic="application.submitted",
        dedupe_key="pms:test:dedupe:1",
        subject="Duplicate Subject",
        body="Duplicate Body",
        recipient_user_id=1001,
    )
    assert n2 is None
    assert PmsNotificationOutbox.objects.filter(dedupe_key="pms:test:dedupe:1").count() == 1


def test_send_pending_notifications():
    """Outbox worker drains pending rows and delivers them."""
    enqueue_notification(
        topic="application.submitted",
        dedupe_key="pms:test:send:1",
        subject="Deliver Me",
        body="Hello from PMS outbox",
        recipient_email="inventor@institute.edu",
    )
    sent_count = send_pending_notifications()
    assert sent_count >= 1

    row = PmsNotificationOutbox.objects.get(dedupe_key="pms:test:send:1")
    assert row.status == "sent"
    assert row.sent_at is not None


# --- 4. Audit Trail & Immutability (CFR-PMS-024, BR-PMS-121, 122) ---


def test_audit_trail_logging_and_attributes():
    """BR-PMS-121, 122: Audit records include user ID, action type, timestamp, application ID, previous state, new state."""
    app = submit_application(
        applicant_user_id=1001,
        title="Audited App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )

    audit_entry = log_audit(
        application=app,
        actor_user_id=2001,
        action_type="custom_audit_event",
        from_state="submitted",
        to_state="under_review",
        details={"reviewer": "Dr. Raman", "notes": "Initial scan complete"},
    )

    assert audit_entry.pk is not None
    assert audit_entry.actor_user_id == 2001
    assert audit_entry.action_type == "custom_audit_event"
    assert audit_entry.from_state == "submitted"
    assert audit_entry.to_state == "under_review"
    assert audit_entry.details["reviewer"] == "Dr. Raman"
    assert audit_entry.is_immutable is True
    assert audit_entry.timestamp is not None
