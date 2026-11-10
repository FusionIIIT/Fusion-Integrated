"""Delivery service: channels, retries, concurrency, recipient groups."""
import threading
from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection
from django.utils import timezone

from modules.vms.models import IntegrationSetting, Notification
from modules.vms.services import delivery
from modules.vms.services.common import notify
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _directory(monkeypatch):
    class U:
        email = "host@example.com"
    monkeypatch.setattr(delivery.directory, "get_users",
                        lambda ids: {i: U() for i in ids})


def test_enqueue_idempotent_on_dedupe_key():
    kw = {"topic": "request.submitted", "dedupe_key": "k1", "subject": "s", "body": "b", "user_id": 1}
    notify.enqueue(**kw)
    notify.enqueue(**kw)
    assert Notification.objects.count() == 2   # inapp + email, once


def test_inapp_marked_sent():
    n = f.make_notification()
    r = delivery.deliver_pending()
    n.refresh_from_db()
    assert n.status == "sent" and n.sent_at and r.sent == 1


def test_email_sent_to_directory_address_and_visitor_address():
    v = f.make_visitor(email="vis@example.com")
    notify.enqueue(topic="request.approved", dedupe_key="a", subject="s", body="b",
                   visitor=v, channels=("email",))
    notify.enqueue(topic="request.reminder", dedupe_key="b", subject="s", body="b",
                   user_id=7, channels=("email",))
    delivery.deliver_pending()
    assert sorted(m.to[0] for m in mail.outbox) == ["host@example.com", "vis@example.com"]


def test_email_failure_retried_then_failed(monkeypatch):
    def boom(**kw):
        raise OSError("smtp down")
    monkeypatch.setattr(delivery, "send_mail", boom)
    n = f.make_notification(channel="email")
    t = timezone.now()
    waits = [0, 1, 5, 30, 30]
    for i, w in enumerate(waits):
        t += timedelta(minutes=w)
        delivery.deliver_pending(now=t)
        n.refresh_from_db()
        assert n.attempts == i + 1
        assert n.status == ("failed" if i == 4 else "pending")
    assert "smtp down" in n.last_error


def test_backoff_blocks_early_retry(monkeypatch):
    monkeypatch.setattr(delivery, "send_mail", lambda **kw: (_ for _ in ()).throw(OSError("x")))
    n = f.make_notification(channel="email")
    t = timezone.now()
    delivery.deliver_pending(now=t)
    delivery.deliver_pending(now=t + timedelta(seconds=10))
    n.refresh_from_db()
    assert n.attempts == 1


def test_loop_survives_one_bad_row(monkeypatch):
    calls = []

    def flaky(**kw):
        calls.append(kw["recipient_list"])
        if len(calls) == 1:
            raise OSError("x")
    monkeypatch.setattr(delivery, "send_mail", flaky)
    f.make_notification(channel="email")
    f.make_notification(channel="email")
    r = delivery.deliver_pending()
    assert r.sent == 1 and r.retrying == 1


def test_sms_skipped_without_gateway():
    n = f.make_notification(channel="sms", recipient_user_id=None,
                            recipient_visitor=f.make_visitor())
    delivery.deliver_pending()
    n.refresh_from_db()
    assert n.status == "skipped" and "gateway" in n.last_error


def test_sms_with_gateway_uses_registered_sender(monkeypatch):
    f.make_integration_setting(key="sms_gateway", value={"url": "x"})
    sent = []
    monkeypatch.setattr(delivery, "_SENDERS", {"sms": lambda row, addr: sent.append(addr)})
    v = f.make_visitor(phone="9000000001")
    f.make_notification(channel="sms", recipient_user_id=None, recipient_visitor=v)
    delivery.deliver_pending()
    assert sent == ["9000000001"]


def test_sms_gateway_without_sender_is_skipped():
    f.make_integration_setting(key="sms_gateway", value={})
    n = f.make_notification(channel="sms", recipient_user_id=None,
                            recipient_visitor=f.make_visitor())
    delivery.deliver_pending()
    n.refresh_from_db()
    assert n.status == "skipped" and IntegrationSetting.objects.count() == 1


def test_second_run_does_not_resend():
    f.make_notification(channel="email")
    delivery.deliver_pending()
    delivery.deliver_pending()
    assert len(mail.outbox) == 1


def test_security_notification_follows_reassignment():
    now = timezone.now()
    zone = f.make_zone()
    old = f.make_role_assignment(user_id=3001, scope_type="zone", scope_id=zone.pk)
    f.make_role_assignment(user_id=3002, scope_type="zone", scope_id=zone.pk)
    f.make_role_assignment(user_id=3003, scope_type="zone", scope_id=zone.pk + 99)
    f.make_role_assignment(user_id=3004, scope_type="campus", starts_at=now + timedelta(days=1),
                           ends_at=now + timedelta(days=2))
    old.revoked_at = now
    old.save()
    delivery.notify_role_holders(topic="zone.violation", dedupe_key="zv:1", subject="s",
                                 body="b", zone_id=zone.pk, channels=("inapp",))
    assert set(Notification.objects.values_list("recipient_user_id", flat=True)) == {3002}


def test_retry_failed_requeues_and_audits():
    n = f.make_notification(status="failed", attempts=5, last_error="x")
    delivery.retry_failed(n.pk, actor=f.make_actor())
    n.refresh_from_db()
    assert n.status == "pending" and n.attempts == 0


@pytest.mark.django_db(transaction=True)
def test_two_workers_deliver_the_same_row_once(monkeypatch):
    f.make_notification(channel="email")
    barrier = threading.Barrier(2)
    sent = []

    def slow(**kw):
        sent.append(1)
        import time
        time.sleep(0.3)

    monkeypatch.setattr(delivery, "send_mail", slow)

    def worker():
        try:
            barrier.wait(timeout=5)
            delivery.deliver_pending()
        finally:
            connection.close()

    ts = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(sent) == 1


def test_backoff_uses_next_attempt_at_column(monkeypatch):
    monkeypatch.setattr(delivery, "send_mail", lambda **kw: (_ for _ in ()).throw(OSError("x")))
    n = f.make_notification(channel="email")
    t = timezone.now()
    delivery.deliver_pending(now=t)
    n.refresh_from_db()
    assert n.next_attempt_at == t + timedelta(minutes=1)
    assert n.last_error == "OSError: x"          # no timestamp prefix
    monkeypatch.setattr(delivery, "send_mail", lambda **kw: 1)
    delivery.deliver_pending(now=t + timedelta(minutes=1))
    n.refresh_from_db()
    assert n.status == "sent" and n.next_attempt_at is None


def test_role_holder_notice_skipped_after_reassignment():
    zone = f.make_zone()
    ra = f.make_role_assignment(user_id=777, role="security", scope_type="zone", scope_id=zone.pk)
    rows = delivery.notify_role_holders(topic="zone.violation", dedupe_key="zv:1", subject="s",
                                        body="b", zone_id=zone.pk, channels=("inapp",))
    assert rows[0].detail["zone_id"] == zone.pk
    ra.revoked_at = timezone.now()
    ra.save()
    delivery.deliver_pending()
    rows[0].refresh_from_db()
    assert rows[0].status == "skipped" and "no longer holds" in rows[0].last_error
