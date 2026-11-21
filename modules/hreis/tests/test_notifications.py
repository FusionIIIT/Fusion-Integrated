"""Spec-driven reminder/deadline events, recipient isolation and mail handoff."""

from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.hreis.models import (
    AppraisalDetail,
    ApprovalRouteStep,
    AuditEvent,
    HRPolicyVersion,
    HRRequest,
    Notification,
    OutboxEvent,
)
from modules.hreis.services import notifications as ns

pytestmark = pytest.mark.django_db


def policy(family="leave", conditions=None):
    now = timezone.now()
    return HRPolicyVersion.objects.create(
        family=family,
        version=1,
        effective_from=now - timedelta(days=1),
        parameters={"conditions": conditions or {}},
        approved_by_user_id=99,
        approved_designation="hradmin",
    )


def pending_request(p, family="leave", owner=10, state="pending_authority", designation="HOD (CSE)"):
    row = HRRequest.objects.create(
        user_id=owner, family=family, state=state,
        policy_version=p, route_step=0, version=1,
    )
    if designation:
        ApprovalRouteStep.objects.create(
            request=row, position=0, designation=designation, policy_version_label="demo"
        )
    HRRequest.objects.filter(pk=row.pk).update(
        updated_at=timezone.now() - timedelta(hours=3)
    )
    return HRRequest.objects.get(pk=row.pk)


def test_hr_uc_021_reminder_only_for_current_configured_authority_and_once():
    # HR-AFR-079, HR-AFR-081, BR-HR-024, BR-HR-033:
    # only configured current assignees receive a single dashboard reminder.
    # HR-CFR-011, HR-UC-021, BR-HR-024, BR-HR-033.
    p = policy(conditions={
        "pending_reminder_after_hours": 2,
        "reminder_recipients": {"HOD (CSE)": [10, 200], "Registrar": [201]},
    })
    row = pending_request(p)
    assert ns.create_pending_action_reminders() == 1
    assert ns.create_pending_action_reminders() == 0
    notice = Notification.objects.get()
    assert notice.recipient_user_id == 200
    assert notice.request_id == row.pk
    assert "assigned action" in notice.message
    assert OutboxEvent.objects.filter(event_type="hreis.notification").count() == 1
    assert AuditEvent.objects.filter(action="notification_generated").count() == 1
    row.refresh_from_db()
    assert row.state == "pending_authority" and row.version == 1

    row.state = "approved"
    row.save(update_fields=["state", "updated_at"])
    assert ns.create_pending_action_reminders() == 0
    assert Notification.objects.count() == 1


def test_hr_uc_021_unconfigured_or_not_due_does_not_notify():
    p = policy(conditions={
        "pending_reminder_after_hours": 10,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    assert ns.create_pending_action_reminders() == 0
    assert not Notification.objects.exists()


def test_hr_uc_021_appraisal_ignores_unassigned_same_role_reviewer():
    p = policy("appraisal", {
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200, 201]},
    })
    row = pending_request(p, family="appraisal", state="pending_review")
    AppraisalDetail.objects.create(
        request=row, period_key="FY2026", reviewer_user_ids=[200],
        submitted_form={"summary": "teaching"},
    )
    assert ns.create_pending_action_reminders() == 1
    assert list(Notification.objects.values_list("recipient_user_id", flat=True)) == [200]


def test_hr_uc_021_no_assignment_means_no_notification():
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p, designation=None)
    assert ns.create_pending_action_reminders() == 0
    assert not Notification.objects.exists()


def test_hr_uc_022_policy_notice_only_when_explicitly_due_and_idempotent():
    # HR-AFR-005, HR-AFR-080, HR-AFR-081, BR-HR-024:
    # no institution policy or deadline is invented by the notification worker.
    # HR-UC-022: no synthetic policy content and no undocumented broadcast.
    now = timezone.now()
    policy("leave", {
        "policy_notice_at": (now - timedelta(minutes=5)).isoformat(),
        "policy_notice_recipients": [200],
    })
    assert ns.create_policy_deadline_notifications() == 1
    assert ns.create_policy_deadline_notifications() == 0
    notice = Notification.objects.get()
    assert notice.request_id is None
    assert notice.recipient_user_id == 200
    assert AuditEvent.objects.get().resource_kind == "policy"


def test_worker_hand_off_retries_then_marks_success_only_on_mail_backend_acceptance(
    monkeypatch,
):
    # HR-AFR-082, BR-HR-024: SMTP handoff is retried and marked only
    # after the configured backend accepts the one intended recipient.
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    ns.create_pending_action_reminders()
    event = OutboxEvent.objects.get()
    monkeypatch.setattr(ns, "get_users", lambda ids: {
        200: SimpleNamespace(email="configured@example.edu")
    })
    with patch.object(ns, "send_mail", side_effect=OSError("mail backend unavailable")):
        assert ns.deliver_pending_notifications() == (0, 1)
    event.refresh_from_db()
    assert event.attempts == 1 and event.dispatched_at is None

    with patch.object(ns, "send_mail", return_value=1) as send:
        assert ns.deliver_pending_notifications() == (1, 0)
    send.assert_called_once()
    assert send.call_args.kwargs["recipient_list"] == ["configured@example.edu"]
    event.refresh_from_db()
    assert event.attempts == 2 and event.dispatched_at is not None
    assert ns.deliver_pending_notifications() == (0, 0)


def test_no_unapproved_automatic_notification_cadence(monkeypatch):
    from modules.hreis.schedule import configured_beat_schedule

    monkeypatch.delenv("HREIS_REMINDER_POLL_MINUTES", raising=False)
    monkeypatch.delenv("HREIS_DELIVERY_POLL_MINUTES", raising=False)
    assert configured_beat_schedule() == {}

    monkeypatch.setenv("HREIS_REMINDER_POLL_MINUTES", "15")
    monkeypatch.setenv("HREIS_DELIVERY_POLL_MINUTES", "5")
    configured = configured_beat_schedule()
    assert set(configured) == {"hreis.generate-reminders", "hreis.deliver-emails"}
    with pytest.raises(ValueError):
        monkeypatch.setenv("HREIS_REMINDER_POLL_MINUTES", "-1")
        configured_beat_schedule()


def test_unknown_directory_email_keeps_outbox_unmarked(monkeypatch):
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    ns.create_pending_action_reminders()
    monkeypatch.setattr(ns, "get_users", lambda ids: {})
    assert ns.deliver_pending_notifications() == (0, 1)
    assert OutboxEvent.objects.get().dispatched_at is None


def test_manual_notification_command_and_celery_schedule():
    # HR-UC-021/022: task names must resolve on a real Celery app.
    from config.celery import app

    app.autodiscover_tasks(force=True)
    assert "hreis.generate_notifications" in app.tasks
    assert "hreis.deliver_notifications" in app.tasks
    text = StringIO()
    call_command("hreis_notifications", "--status", stdout=text)
    assert "0 pending" in text.getvalue()
    text = StringIO()
    call_command("hreis_notifications", "--generate", stdout=text)
    assert "Generated 0 reminders and 0 policy notices" in text.getvalue()


@pytest.mark.parametrize("conditions", [
    {"pending_reminder_after_hours": 0, "reminder_recipients": {"HOD (CSE)": [200]}},
    {"pending_reminder_after_hours": 2, "reminder_recipients": {"Unknown": [200]}},
    {"pending_reminder_after_hours": 2, "reminder_recipients": {"HOD (CSE)": [200, 200]}},
    {"policy_notice_at": "2026-01-01", "policy_notice_recipients": [200]},
    {"policy_notice_recipients": [200]},
])
def test_invalid_notification_policy_not_published(conditions):
    from core.api.exceptions import BadRequestError
    from modules.hreis.services.policies import _check_parameters

    with pytest.raises(BadRequestError):
        _check_parameters("leave", {"conditions": conditions})


def test_notification_worker_leaves_identity_service_failure_pending(monkeypatch):
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    assert ns.create_pending_action_reminders() == 1

    def unavailable(ids):
        raise ConnectionError("Identity lookup temporarily unavailable")

    monkeypatch.setattr(ns, "get_users", unavailable)
    with patch.object(ns, "send_mail") as mail:
        assert ns.deliver_pending_notifications() == (0, 1)
    mail.assert_not_called()
    event = OutboxEvent.objects.get()
    assert event.dispatched_at is None
    assert event.attempts == 0


def test_notification_backend_returning_zero_is_not_delivery(monkeypatch):
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    ns.create_pending_action_reminders()
    monkeypatch.setattr(ns, "get_users", lambda ids: {
        200: SimpleNamespace(email="configured@example.edu")
    })
    with patch.object(ns, "send_mail", return_value=0):
        assert ns.deliver_pending_notifications() == (0, 1)
    event = OutboxEvent.objects.get()
    assert event.attempts == 1 and event.dispatched_at is None


def test_notification_retry_limit_and_requeue_only_explicitly(monkeypatch):
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    ns.create_pending_action_reminders()
    outbox = OutboxEvent.objects.get()
    outbox.attempts = 5
    outbox.save(update_fields=["attempts"])
    monkeypatch.setattr(ns, "get_users", lambda ids: {
        200: SimpleNamespace(email="configured@example.edu")
    })
    with patch.object(ns, "send_mail") as send:
        assert ns.deliver_pending_notifications() == (0, 0)
    send.assert_not_called()
    text = StringIO()
    call_command("hreis_notifications", "--status", stdout=text)
    assert "1 pending, 1 exhausted" in text.getvalue()
    text = StringIO()
    call_command("hreis_notifications", "--retry-failed", stdout=text)
    assert "Requeued 1" in text.getvalue()
    assert OutboxEvent.objects.get().attempts == 0


def test_notification_generation_skips_invalid_policy_dates_and_recipients():
    now = timezone.now()
    policy("ltc", {
        "policy_notice_at": "not-a-timestamp",
        "policy_notice_recipients": [200],
    })
    policy("cpda", {
        "policy_notice_at": (now + timedelta(days=1)).isoformat(),
        "policy_notice_recipients": [200],
    })
    assert ns.create_policy_deadline_notifications() == 0
    assert not Notification.objects.exists()


def test_notification_commands_refuse_zero_delivery_limit():
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match="positive"):
        call_command("hreis_notifications", "--deliver", "--limit=0", stdout=StringIO())


def test_notification_worker_accepts_valid_delivery_command(monkeypatch):
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    ns.create_pending_action_reminders()
    monkeypatch.setattr(ns, "get_users", lambda ids: {
        200: SimpleNamespace(email="configured@example.edu")
    })
    with patch.object(ns, "send_mail", return_value=1):
        text = StringIO()
        call_command("hreis_notifications", "--deliver", stdout=text)
    assert "Handed 1 message" in text.getvalue()
    assert OutboxEvent.objects.get().dispatched_at is not None


def test_email_worker_never_consumes_non_email_hr_outbox_events(monkeypatch):
    # HR-CFR-011 and BR-HR-024: workflow/policy outbox events are not email.
    non_email_keys = ("transition-not-email", "policy-not-email")
    for key, kind in zip(
        non_email_keys,
        ("hreis.request_transition", "hreis.policy_published"),
        strict=True,
    ):
        OutboxEvent.objects.create(
            event_key=key, event_type=kind,
            payload={"resource_id": 42},
        )
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    assert ns.create_pending_action_reminders() == 1
    monkeypatch.setattr(ns, "get_users", lambda ids: {
        200: SimpleNamespace(email="active@example.edu", is_active=True)
    })
    with patch.object(ns, "send_mail", return_value=1) as mail:
        assert ns.deliver_pending_notifications() == (1, 0)
    mail.assert_called_once()
    for row in OutboxEvent.objects.filter(event_key__in=non_email_keys):
        assert row.attempts == 0 and row.dispatched_at is None
    text = StringIO()
    call_command("hreis_notifications", "--status", stdout=text)
    assert "0 pending" in text.getvalue()
    OutboxEvent.objects.filter(event_key__in=non_email_keys).update(attempts=5)
    text = StringIO()
    call_command("hreis_notifications", "--retry-failed", stdout=text)
    assert "Requeued 0" in text.getvalue()
    assert set(OutboxEvent.objects.filter(
        event_key__in=non_email_keys
    ).values_list("attempts", flat=True)) == {5}


def test_inactive_iam_user_must_not_receive_hr_email(monkeypatch):
    # HR-AFR-098 / BR-HR-030: no sensitive mail to a disabled account.
    p = policy(conditions={
        "pending_reminder_after_hours": 1,
        "reminder_recipients": {"HOD (CSE)": [200]},
    })
    pending_request(p)
    assert ns.create_pending_action_reminders() == 1
    monkeypatch.setattr(ns, "get_users", lambda ids: {
        200: SimpleNamespace(email="former.staff@example.edu", is_active=False)
    })
    with patch.object(ns, "send_mail") as mail:
        assert ns.deliver_pending_notifications() == (0, 1)
    mail.assert_not_called()
    event = OutboxEvent.objects.get()
    assert event.attempts == 1 and event.dispatched_at is None
