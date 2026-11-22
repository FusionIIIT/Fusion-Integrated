"""Scheduler and notification-channel edge cases: when a reminder is skipped, how failures
in one row are contained, and every accepted shape of the notification_channels setting
(UC-037, UC-040, BR-062, BR-174, BR-200)."""
import logging
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.vms.domain import request_state as rs
from modules.vms.models import Notification
from modules.vms.services import delivery, scheduler_work
from modules.vms.services.common import notify
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db
T0 = "2026-06-01 09:00:00+00:00"
LATER = "2026-06-01 22:00:00+00:00"          # 13 h later: past the 12 h reminder, before expiry


@pytest.fixture(autouse=True)
def _directory(monkeypatch):
    class U:
        email = "host@example.com"
    monkeypatch.setattr(delivery.directory, "get_users", lambda ids: {i: U() for i in ids})


def _policy(timeout=24, reminder=12):
    f.make_published_policy(version=1, approval_timeout_hours=timeout,
                            reminder_after_hours=reminder,
                            published_at=timezone.now() - timedelta(days=1))


def _request(**kw):
    with freeze_time(T0):
        _policy()
        return f.make_visit_request(**kw)


# --- reminders ---------------------------------------------------------------------------

def test_reminder_is_not_sent_before_the_reminder_time():
    _request(status="pending")
    with freeze_time("2026-06-01 20:00:00+00:00"):           # 11 h in
        assert scheduler_work.send_reminders() == 0


def test_reminder_is_not_sent_once_the_request_is_past_its_expiry():
    _request(status="pending")
    with freeze_time("2026-06-02 10:00:00+00:00"):           # 25 h in
        assert scheduler_work.send_reminders() == 0


def test_reminder_goes_to_the_host_once_only():
    req = _request(status="pending")
    with freeze_time(LATER):
        assert scheduler_work.send_reminders() == 1
        assert scheduler_work.send_reminders() == 0
    assert Notification.objects.filter(topic="request.reminder",
                                       recipient_user_id=req.host_user_id).count() >= 1


def test_urgent_request_reminder_goes_to_admins_not_the_host():
    with freeze_time(T0):
        f.make_role_assignment(user_id=4001, role="admin")
    req = _request(status="awaiting_admin", is_urgent=True)
    with freeze_time(LATER):
        assert scheduler_work.send_reminders() == 1
    assert Notification.objects.filter(topic="request.reminder",
                                       recipient_user_id=4001).exists()
    assert not Notification.objects.filter(topic="request.reminder",
                                           recipient_user_id=req.host_user_id).exists()


def test_one_failing_reminder_does_not_stop_the_others(monkeypatch, caplog):
    a = _request(status="pending")
    with freeze_time(T0):
        b = f.make_visit_request(status="pending")
    real = scheduler_work.notify.enqueue

    def flaky(**kw):
        if kw.get("dedupe_key") == f"request.reminder:{a.pk}":
            raise RuntimeError("mail backend down")
        return real(**kw)

    monkeypatch.setattr(scheduler_work.notify, "enqueue", flaky)
    with freeze_time(LATER), caplog.at_level(logging.ERROR):
        assert scheduler_work.send_reminders() == 1
    assert "vms.scheduler.reminder_failed" in caplog.text
    a.refresh_from_db()
    b.refresh_from_db()
    assert a.reminded_at is None and b.reminded_at is not None   # a is retried next run


# --- expiry ------------------------------------------------------------------------------

def test_expiry_skips_a_request_that_is_no_longer_waiting():
    req = _request(status="pending")
    type(req).objects.filter(pk=req.pk).update(status="approved")
    with freeze_time("2026-06-03 09:00:00+00:00"):
        assert scheduler_work.expire_pending() == 0


def test_expiry_logs_and_continues_when_the_state_table_has_no_expiry_move(monkeypatch, caplog):
    _request(status="pending")

    def no_move(*a, **k):
        raise rs.InvalidTransition("pre_registered", "pending", "auto_expire", "system")

    monkeypatch.setattr(scheduler_work.rs, "next_state", no_move)
    with freeze_time("2026-06-03 09:00:00+00:00"), caplog.at_level(logging.WARNING):
        assert scheduler_work.expire_pending() == 0
    assert "vms.scheduler.no_expiry_move" in caplog.text


def test_expiry_contains_an_unexpected_failure_in_one_row(monkeypatch, caplog):
    first = _request(status="pending")
    with freeze_time(T0):
        second = f.make_visit_request(status="pending")
    real = scheduler_work.notify.enqueue

    def flaky(**kw):
        if kw.get("dedupe_key") == f"request.expired:{first.pk}:visitor":
            raise RuntimeError("boom")
        return real(**kw)

    monkeypatch.setattr(scheduler_work.notify, "enqueue", flaky)
    with freeze_time("2026-06-03 09:00:00+00:00"), caplog.at_level(logging.ERROR):
        assert scheduler_work.expire_pending() == 1
    assert "vms.scheduler.expiry_failed" in caplog.text
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == "pending" and second.status == "expired"   # first rolled back


# --- notification_channels (BR-174) ------------------------------------------------------

ALL = ("inapp", "email", "sms", "push")


def _setting(value):
    if value is not None:
        f.make_integration_setting(key="notification_channels", value=value)


@pytest.mark.parametrize("value, expected", [
    (None, ALL),                                              # never configured: all on
    ({}, ALL),
    ({"sms": False}, ("inapp", "email", "push")),             # flat map, absent stays on
    ({"inapp": True, "email": False, "sms": False, "push": False}, ("inapp",)),
    (["inapp", "email"], ("inapp", "email")),                 # list of enabled channels
    ({"request.reminder": ["email"], "default": ["inapp"]}, ("email",)),   # per topic
    ({"other.topic": ["email"], "default": ["inapp"]}, ("inapp",)),        # topic default
    ({"other.topic": ["email"], "*": ["push"]}, ("push",)),                # wildcard
])
def test_enabled_channels_accepts_every_documented_shape(value, expected):
    _setting(value)
    assert tuple(notify._enabled_channels("request.reminder", ALL)) == expected
