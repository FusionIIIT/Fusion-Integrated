"""Notification delivery and scheduled reminder behavior."""

import smtplib
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from modules.hr import tasks
from modules.hr.models import (
    AuditEvent,
    Claim,
    EmployeeRecord,
    HRNotification,
    LeaveRequest,
    WorkflowRoute,
)

pytestmark = pytest.mark.django_db


def pending_email(recipient, suffix):
    return HRNotification.objects.create(
        recipient_user_id=recipient,
        topic="hr.notice",
        dedupe_key=f"email:{suffix}",
        subject=f"Subject {suffix}",
        body=f"Body {suffix}",
    )


def test_delivery_marks_sent_missing_email_smtp_error_and_backend_rejection(monkeypatch):
    sent = pending_email(1, "sent")
    missing = pending_email(2, "missing")
    smtp_error = pending_email(3, "smtp")
    rejected = pending_email(4, "rejected")
    monkeypatch.setattr(
        tasks.directory,
        "get_users",
        lambda user_ids: {
            1: SimpleNamespace(email="sent@example.test"),
            3: SimpleNamespace(email="smtp@example.test"),
            4: SimpleNamespace(email="rejected@example.test"),
        },
    )

    def send_mail(*, recipient_list, **kwargs):
        email = recipient_list[0]
        if email == "smtp@example.test":
            raise smtplib.SMTPException("relay unavailable")
        return int(email == "sent@example.test")

    monkeypatch.setattr(tasks, "send_mail", send_mail)
    assert tasks.deliver_notifications(limit=500) == {"sent": 1, "failed": 3, "deferred": 0}
    for row_id, status, error in [
        (sent.pk, "sent", ""),
        (missing.pk, "failed", "No official email address is available."),
        (smtp_error.pk, "failed", "SMTPException"),
        (rejected.pk, "failed", "EmailBackendRejectedMessage"),
    ]:
        row = HRNotification.objects.get(pk=row_id)
        assert row.email_status == status
        assert row.email_attempts == 1
        assert row.email_error == error


def test_delivery_clamps_batch_limit_and_defers_row_claimed_by_another_worker(monkeypatch):
    first = pending_email(1, "first")
    second = pending_email(1, "second")
    monkeypatch.setattr(
        tasks.directory, "get_users", lambda user_ids: {1: SimpleNamespace(email="hr@example.test")}
    )
    monkeypatch.setattr(tasks, "send_mail", lambda **kwargs: 1)
    assert tasks.deliver_notifications(limit=0) == {"sent": 1, "failed": 0, "deferred": 0}
    assert tasks.deliver_notifications(limit=5000) == {"sent": 1, "failed": 0, "deferred": 0}
    assert HRNotification.objects.filter(email_status="sent").count() == 2

    raced = pending_email(1, "raced")
    original_filter = HRNotification.objects.filter

    def concurrent_claim_filter(*args, **kwargs):
        queryset = original_filter(*args, **kwargs)
        if kwargs == {"pk": raced.pk, "email_status": "pending"}:
            return SimpleNamespace(update=lambda **updates: 0)
        return queryset

    monkeypatch.setattr(HRNotification.objects, "filter", concurrent_claim_filter)
    assert tasks.deliver_notifications() == {"sent": 0, "failed": 0, "deferred": 1}
    raced.refresh_from_db()
    assert raced.email_status == "pending"
    assert (
        HRNotification.objects.filter(pk__in=[first.pk, second.pk], email_status="sent").count()
        == 2
    )


def test_pending_reminders_cover_claim_leave_recent_and_unconfigured_routes():
    employee = EmployeeRecord.objects.create(
        user_id=1001,
        employee_category="staff",
        department="Research",
        designation="Officer",
        created_by_user_id=7,
        updated_by_user_id=7,
    )
    WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="ltc_advance",
        steps=[{"approver_user_id": 88}],
        reminder_after_hours=1,
        updated_by_user_id=7,
    )
    WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="leave_casual",
        steps=[{"approver_user_id": 89}],
        reminder_after_hours=1,
        updated_by_user_id=7,
    )
    now = timezone.now()
    old_claim = Claim.objects.create(
        employee_user_id=1001,
        employee_category="staff",
        request_type="ltc_advance",
        form_data={"destination": "Pune"},
        status="pending_authority",
        current_authority_user_id=88,
    )
    recent_claim = Claim.objects.create(
        employee_user_id=1001,
        employee_category="staff",
        request_type="ltc_advance",
        form_data={"destination": "Jaipur"},
        status="pending_authority",
        current_authority_user_id=88,
    )
    unconfigured = Claim.objects.create(
        employee_user_id=1001,
        employee_category="staff",
        request_type="cpda_advance",
        amount="1.00",
        status="pending_authority",
        current_authority_user_id=90,
    )
    old_leave = LeaveRequest.objects.create(
        employee=employee,
        leave_type="casual",
        duration_days="1.00",
        justification="Family",
        route_snapshot=[{"approver_user_id": 89}],
        current_authority_user_id=89,
        submitted_by_user_id=1001,
    )
    recent_leave = LeaveRequest.objects.create(
        employee=employee,
        leave_type="casual",
        duration_days="1.00",
        justification="Medical appointment",
        route_snapshot=[{"approver_user_id": 89}],
        current_authority_user_id=89,
        submitted_by_user_id=1001,
    )
    unconfigured_leave = LeaveRequest.objects.create(
        employee=employee,
        leave_type="earned",
        duration_days="1.00",
        justification="Family",
        route_snapshot=[{"approver_user_id": 90}],
        current_authority_user_id=90,
        submitted_by_user_id=1001,
    )
    old = now - timedelta(hours=2)
    Claim.objects.filter(pk=old_claim.pk).update(updated_at=old)
    Claim.objects.filter(pk=unconfigured.pk).update(updated_at=old)
    LeaveRequest.objects.filter(pk=old_leave.pk).update(updated_at=old)
    LeaveRequest.objects.filter(pk=unconfigured_leave.pk).update(updated_at=old)

    assert tasks.generate_pending_reminders(now_iso=now.isoformat()) == 2
    assert tasks.generate_pending_reminders() == 0
    assert (
        HRNotification.objects.filter(
            topic__in=["claim.pending_reminder", "leave.pending_reminder"]
        ).count()
        == 2
    )
    assert (
        AuditEvent.objects.filter(
            action__in=["claim.reminder_generated", "leave.reminder_generated"]
        ).count()
        == 2
    )
    assert Claim.objects.filter(pk=recent_claim.pk).exists()
    assert LeaveRequest.objects.filter(pk=recent_leave.pk).exists()
