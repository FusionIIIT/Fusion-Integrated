"""Ops gaps: visitor notifications, reminders, expiry and delivery."""
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.vms.models import Notification, VisitLog, VisitRequest
from modules.vms.services import delivery, scheduler_work
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"
T0 = "2026-06-01 09:00:00+00:00"


def _setup(timeout=24, reminder=12, **req):
    f.make_published_policy(version=1, approval_timeout_hours=timeout,
                            reminder_after_hours=reminder,
                            published_at=timezone.now() - timedelta(days=1))
    return f.make_visit_request(**req)


def test_uc_030_visitor_mark_notification_read_and_unread_count(visitor_client):
    """VMS-UC-030: visitor session read/unread."""
    c, v = visitor_client
    a = f.make_notification(recipient_user_id=None, recipient_visitor=v)
    f.make_notification(recipient_user_id=None, recipient_visitor=v)
    assert c.get(BASE + "visitor/notifications").json()["unread"] == 2
    assert c.post(BASE + f"visitor/notifications/{a.pk}/read").status_code == 200
    assert c.get(BASE + "visitor/notifications").json()["unread"] == 1
    unread = c.get(BASE + "visitor/notifications?unread=1").json()["results"]
    assert a.pk not in {r["id"] for r in unread}


def test_uc_030_visitor_notifications_ordered_newest_first(visitor_client):
    """VMS-UC-030: ordering."""
    c, v = visitor_client
    rows = [f.make_notification(recipient_user_id=None, recipient_visitor=v) for _ in range(3)]
    base = timezone.now()
    for i, r in enumerate(rows):
        Notification.objects.filter(pk=r.pk).update(created_at=base + timedelta(minutes=i))
    ids = [r["id"] for r in c.get(BASE + "visitor/notifications").json()["results"]]
    assert ids == [rows[2].pk, rows[1].pk, rows[0].pk]


def test_uc_040_reminder_skipped_for_expired_request():
    """VMS-UC-040: no reminder after expiry."""
    with freeze_time(T0):
        req = _setup()
    with freeze_time("2026-06-02 10:00:00+00:00"):
        assert scheduler_work.send_reminders() == 0
    req.refresh_from_db()
    assert req.reminded_at is None
    assert not Notification.objects.filter(topic="request.reminder").exists()


def test_uc_040_reminder_sent_to_host_with_channel_per_setting():
    """VMS-UC-040: recipient and channels."""
    with freeze_time(T0):
        req = _setup(host_user_id=2077)
    with freeze_time("2026-06-01 21:00:00+00:00"):
        assert scheduler_work.send_reminders() == 1
    rows = Notification.objects.filter(topic="request.reminder")
    assert {r.recipient_user_id for r in rows} == {2077}
    assert set(rows.values_list("channel", flat=True)) == {"inapp", "email"}
    assert req.visitor.pk not in {r.recipient_visitor_id for r in rows}


def test_uc_040_reminder_for_urgent_awaiting_admin_goes_to_admins():
    """VMS-UC-040: urgent reminders."""
    with freeze_time(T0):
        f.make_role_assignment(user_id=4001, role="admin")
        _setup(status="awaiting_admin", is_urgent=True)
    with freeze_time("2026-06-01 21:00:00+00:00"):
        scheduler_work.send_reminders()
    assert Notification.objects.filter(topic="request.reminder",
                                       recipient_user_id=4001).exists()


def test_uc_040_reminder_threshold_uses_policy_snapshot():
    """VMS-UC-040: snapshot policy decides the reminder time."""
    with freeze_time(T0):
        req = _setup(timeout=24, reminder=12)
        f.make_published_policy(version=2, approval_timeout_hours=4, reminder_after_hours=1,
                                published_at=timezone.now() + timedelta(minutes=1))
    with freeze_time("2026-06-01 10:30:00+00:00"):
        assert scheduler_work.send_reminders() == 0      # v2 would already have reminded
    req.refresh_from_db()
    assert req.reminded_at is None


def test_uc_037_expiry_notifies_visitor_and_host():
    """VMS-UC-037: both parties get in-app and email notices."""
    with freeze_time(T0):
        req = _setup(host_user_id=2088)
    with freeze_time("2026-06-02 09:00:00+00:00"):
        scheduler_work.expire_pending()
    rows = Notification.objects.filter(topic="request.expired")
    assert set(rows.filter(recipient_visitor=req.visitor).values_list("channel", flat=True)) \
        == {"inapp", "email"}
    assert set(rows.filter(recipient_user_id=2088).values_list("channel", flat=True)) \
        == {"inapp", "email"}


def test_uc_037_expiry_exact_boundary_not_expired_at_equal_instant():
    """VMS-UC-037: one tick before the deadline is not expired; the deadline itself is."""
    with freeze_time(T0):
        req = _setup()
    with freeze_time("2026-06-02 08:59:59.999999+00:00"):
        assert scheduler_work.expire_pending() == 0
    req.refresh_from_db()
    assert req.status == "pending"
    with freeze_time("2026-06-02 09:00:00+00:00"):
        assert scheduler_work.expire_pending() == 1


def test_bw_vms_03_expired_request_then_gate_denies_credential(api_as, gate, guard):
    """BW-VMS-03: an expired request's pass is refused at the gate."""
    with freeze_time(T0):
        req = _setup()
        vp = f.make_visit_pass(visit_request=req, valid_from=timezone.now(),
                               valid_until=timezone.now() + timedelta(days=3))
    with freeze_time("2026-06-02 09:00:00+00:00"):
        scheduler_work.expire_pending()
        req.refresh_from_db()
        assert req.status == "expired"
        c = api_as(user_id=3001, permissions=("vms.gate.operate", "vms.gate.sync"))
        r = c.post(BASE + "gate/validate", {"qr_token": vp.qr_token, "gate_id": gate.pk},
                   format="json")
    assert r.status_code == 403
    assert not VisitLog.objects.filter(visit_pass=vp, event="check_in").exists()


def test_br_062_expiry_does_not_touch_pre_authorized_or_vip_requests():
    """VMS-BR-062: only pending/awaiting_admin requests expire."""
    with freeze_time(T0):
        keep = [_setup(status="approved"),
                f.make_visit_request(status="rejected"),
                f.make_visit_request(status="completed"),
                f.make_visit_request(status="awaiting_admin", source="walk_in")]
    with freeze_time("2026-07-01 09:00:00+00:00"):
        assert scheduler_work.expire_pending() == 0
    assert [VisitRequest.objects.get(pk=r.pk).status for r in keep] == [
        "approved", "rejected", "completed", "awaiting_admin"]


def test_br_174_delivery_skips_channel_disabled_after_enqueue():
    """VMS-BR-174: a channel with no gateway at send time is skipped, not sent."""
    v = f.make_visitor()
    row = f.make_notification(recipient_user_id=None, recipient_visitor=v, channel="sms")
    rep = delivery.deliver_pending()
    row.refresh_from_db()
    assert (rep.skipped, row.status) == (1, "skipped")
    assert "gateway" in row.last_error


def test_uc_030_delivery_inapp_for_visitor_without_email_ok():
    """VMS-UC-030: in-app needs no email; the email channel is skipped, not failed."""
    v = f.make_visitor(email="")
    inapp = f.make_notification(recipient_user_id=None, recipient_visitor=v, channel="inapp")
    mail = f.make_notification(recipient_user_id=None, recipient_visitor=v, channel="email")
    delivery.deliver_pending()
    inapp.refresh_from_db(), mail.refresh_from_db()
    assert inapp.status == "sent"
    assert mail.status == "skipped" and "email" in mail.last_error


def test_uc_030_outbox_retry_requires_permission(api_as):
    """VMS-UC-030: retrying a failed notification needs vms.audit.view."""
    bad = f.make_notification(status="failed", attempts=5)
    r = api_as(permissions=("vms.notification.view_self",)).post(
        BASE + f"notify/outbox/{bad.pk}/retry")
    assert r.status_code == 403
    bad.refresh_from_db()
    assert bad.status == "failed"
